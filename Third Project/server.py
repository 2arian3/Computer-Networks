import time
import json
import socket
import dhcppython
import ipaddress
import asyncio

with open('server_configuration.json') as json_file:
    server_config = json.load(json_file)

SERVER_PORT  = 67
SERVER_IP    = server_config['server_ip']
MAX_MSG_SIZE = 1024


available_ips = []
if server_config['pool_mode'] == 'range':
    start = server_config['range']['from'].split('.')
    start = ''.join(['{0:08b}'.format(int(octet)) for octet in start])

    end = server_config['range']['to'].split('.')
    end = ''.join(['{0:08b}'.format(int(octet)) for octet in end])

    for i in range(int(end, 2) - int(start, 2) + 1):
        address = '{0:032b}'.format(int(start, 2) + i)
        available_ips.append('.'.join([str(int(address[:8], 2)),
                                       str(int(address[8:16], 2)),
                                       str(int(address[16:24], 2)),
                                       str(int(address[24:], 2))]))
elif server_config['pool_mode'] == 'subnet':
    ip_block = server_config['subnet']['ip_block'].split('.')
    ip_block = ''.join(['{0:08b}'.format(int(octet)) for octet in ip_block])

    subnet_mask = server_config['subnet']['subnet_mask'].split('.')
    subnet_mask = ''.join(['{0:08b}'.format(int(octet)) for octet in subnet_mask])
    hosts = 2 ** (32 - subnet_mask.count('1'))

    for i in range(1, hosts-1):
        address = '{0:032b}'.format(int(ip_block, 2) + i)
        available_ips.append('.'.join([str(int(address[:8], 2)),
                                       str(int(address[8:16], 2)),
                                       str(int(address[16:24], 2)),
                                       str(int(address[24:], 2))]))

lease_time = int(server_config['lease_time'])
blocked_clients = server_config['black_list']
reserved_ips = server_config['reservation_list']
available_ips = [available_ip for available_ip in available_ips if available_ip != SERVER_IP and available_ip not in reserved_ips.values()]

given_ips = dict()
client_states = dict()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server_socket.bind(('', SERVER_PORT))


while True:
    data, _ = server_socket.recvfrom(MAX_MSG_SIZE)
    data = dhcppython.packet.DHCPPacket.from_bytes(data)

    if data.options.by_code(53).data == b'\x01':
        if data.chaddr not in blocked_clients:
            requesting_ip = ''
            if data.chaddr.lower() in reserved_ips:
                requesting_ip = reserved_ips[data.chaddr.lower()]
            elif available_ips:
                requesting_ip = available_ips[0]
            offer = dhcppython.packet.DHCPPacket(
                op=data.op,
                htype=data.htype,
                hlen=6,
                hops=0,
                xid=data.xid,
                secs=0,
                flags=0,
                ciaddr=ipaddress.IPv4Address(0),
                yiaddr=ipaddress.IPv4Address(requesting_ip),
                siaddr=ipaddress.IPv4Address(SERVER_IP),
                giaddr=ipaddress.IPv4Address(0),
                chaddr=data.chaddr,
                sname=b'',
                file=b'',
                options=dhcppython.options.OptionList(
                    [
                        dhcppython.options.options.short_value_to_object(51, lease_time),
                        dhcppython.options.options.short_value_to_object(53, 'DHCPOFFER'),
                        dhcppython.options.options.short_value_to_object(54, SERVER_IP)
                    ])
            )
            server_socket.sendto(offer.asbytes, ('<broadcast>', 68))
            client_states[data.xid] = 'offered'

    elif data.xid in client_states and data.options.by_code(53).data == b'\x03' and client_states[data.xid] == 'offered':

        ack = dhcppython.packet.DHCPPacket(
            op=data.op,
            htype=data.htype,
            hlen=6,
            hops=0,
            xid=data.xid,
            secs=0,
            flags=0,
            ciaddr=ipaddress.IPv4Address(0),
            yiaddr=data.ciaddr,
            siaddr=ipaddress.IPv4Address(SERVER_IP),
            giaddr=ipaddress.IPv4Address(0),
            chaddr=data.chaddr,
            sname=b'',
            file=b'',
            options=dhcppython.options.OptionList(
                [
                    dhcppython.options.options.short_value_to_object(51, lease_time),
                    dhcppython.options.options.short_value_to_object(53, 'DHCPACK'),
                    dhcppython.options.options.short_value_to_object(54, SERVER_IP)
                ])
        )
        if ack.yiaddr not in given_ips.values():
            given_ips[ack.chaddr] = ack.yiaddr
            if ack.chaddr.lower() not in reserved_ips:
                available_ips.remove(str(ack.yiaddr))
            server_socket.sendto(ack.asbytes, ('<broadcast>', 68))
            client_states[data.xid] = 'acked'
