import time
import json
import socket
import dhcppython
import ipaddress
import threading
import datetime


class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'


with open('server_configuration.json') as json_file:
    server_config = json.load(json_file)

SERVER_PORT  = 67
CLIENT_PORT  = 68
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

    for i in range(1, hosts - 1):
        address = '{0:032b}'.format(int(ip_block, 2) + i)
        available_ips.append('.'.join([str(int(address[:8], 2)),
                                       str(int(address[8:16], 2)),
                                       str(int(address[16:24], 2)),
                                       str(int(address[24:], 2))]))

lease_time = int(server_config['lease_time'])
blocked_clients = server_config['black_list']
reserved_ips = server_config['reservation_list']
available_ips = [available_ip for available_ip in available_ips if
                 available_ip != SERVER_IP and available_ip not in reserved_ips.values()]

mac_to_ip = dict()
ip_to_lease_time = dict()
client_states = dict()
information = dict()
lock = threading.Lock()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server_socket.bind(('', SERVER_PORT))


def add_client_information(mac_address, name, ip_address, expire_time):
    information[mac_address] = dict()
    information[mac_address]['name'] = name
    information[mac_address]['ip_address'] = ip_address
    information[mac_address]['expire_time'] = datetime.datetime.now() + datetime.timedelta(seconds=expire_time)


def update_ip_pool():

    to_be_removed = []
    for mac_address, ip_address in mac_to_ip.items():
        if time.time() - ip_to_lease_time[ip_address] >= lease_time:
            to_be_removed.append((mac_address, ip_address))
    for item in to_be_removed:
        del mac_to_ip[item[0]]
        del ip_to_lease_time[item[1]]
        del client_states[item[0]]
        del information[item[0]]
        if item[1] not in reserved_ips.values():
            available_ips.append(item[1])


def handle_client(data):
    if data.options.by_code(53).data == b'\x01':
        if data.chaddr.lower() not in blocked_clients:
            requesting_ip = ''

            lock.acquire()
            update_ip_pool()
            lock.release()

            if data.chaddr.lower() in mac_to_ip:
                requesting_ip = mac_to_ip[data.chaddr.lower()]
            elif data.chaddr.lower() in reserved_ips:
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
            server_socket.sendto(offer.asbytes, ('<broadcast>', CLIENT_PORT))
            client_states[data.chaddr.lower()] = 'offered'

    elif data.chaddr.lower() in client_states and data.options.by_code(53).data == b'\x03' and client_states[data.chaddr.lower()] == 'offered':

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

        if ack.chaddr.lower() in mac_to_ip and time.time() - ip_to_lease_time[ack.yiaddr]:
            lock.acquire()
            ip_to_lease_time[ack.yiaddr] = time.time()
            add_client_information(
                ack.chaddr.lower(),
                data.options.by_code(12).data.decode(),
                ack.yiaddr,
                lease_time
            )
            lock.release()
            server_socket.sendto(ack.asbytes, ('<broadcast>', CLIENT_PORT))
            client_states[data.chaddr.lower()] = 'acked'

        elif ack.yiaddr not in ip_to_lease_time:
            lock.acquire()
            mac_to_ip[ack.chaddr.lower()] = ack.yiaddr
            ip_to_lease_time[ack.yiaddr] = time.time()
            if ack.chaddr.lower() not in reserved_ips:
                available_ips.remove(str(ack.yiaddr))
            add_client_information(
                ack.chaddr.lower(),
                data.options.by_code(12).data.decode(),
                ack.yiaddr,
                lease_time
            )
            lock.release()
            server_socket.sendto(ack.asbytes, ('<broadcast>', CLIENT_PORT))
            client_states[data.chaddr.lower()] = 'acked'


def log():
    while True:
        if input('Enter show_clients to see more information...\n') == 'show_clients':
            print(f'{Colors.WARNING}Computer Name\tMAC Address\t\t IP Address\t\tExpire Time')

            lock.acquire()
            update_ip_pool()
            lock.release()

            for client in information:
                t = information[client]
                print(f'{Colors.CYAN}{t["name"]}\t{client}\t{t["ip_address"]}\t{t["expire_time"]}')


threading.Thread(target=log).start()

while True:
    data, _ = server_socket.recvfrom(MAX_MSG_SIZE)
    data = dhcppython.packet.DHCPPacket.from_bytes(data)

    threading.Thread(target=handle_client, args=(data,)).start()
