import random
import socket
import dhcppython
import ipaddress
import signal
import time
import sys

MAC_ADDRESS  = 'fe:1a:b2:ef:1b:a0'
CLIENT_PORT  = 68
GOT_IP       = False
CLIENT_IP    = ''
LEASE_TIME   = 0
MAX_MSG_SIZE = 1024


# Generating next timeout based on last time-out and backoff-cutoff.
# Excluding 0 from random numbers.
def discover_timeout(last_timeout, backoff_cutoff=120):
    return min(2 * (1.0-random.random()) * last_timeout, backoff_cutoff) \
           if last_timeout != backoff_cutoff else backoff_cutoff


def handle(signum, frame):
    raise Exception('Timeout...')


client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
client_socket.bind(('', CLIENT_PORT))

discover = dhcppython.packet.DHCPPacket(
    op='BOOTREQUEST',
    htype='ETHERNET',
    hlen=6,
    hops=0,
    xid=random.randint(1, 2 ** 32),
    secs=0,
    flags=0,
    ciaddr=ipaddress.IPv4Address(0),
    yiaddr=ipaddress.IPv4Address(0),
    siaddr=ipaddress.IPv4Address(0),
    giaddr=ipaddress.IPv4Address(0),
    chaddr=MAC_ADDRESS,
    sname=b'',
    file=b'',
    options=dhcppython.options.OptionList([dhcppython.options.options.short_value_to_object(53, 'DHCPDISCOVER')])
)

time_out_interval = 10
signal.signal(signal.SIGALRM, handle)
signal.alarm(time_out_interval)

while True:
    client_socket.sendto(discover.asbytes, ('<broadcast>', 67))
    try:
        offer, _ = client_socket.recvfrom(MAX_MSG_SIZE)
        offer = dhcppython.packet.DHCPPacket.from_bytes(offer)

        if offer.xid == discover.xid and offer.options.by_code(53).data == b'\x02':
            request = dhcppython.packet.DHCPPacket(
                op=discover.op,
                htype=discover.htype,
                hlen=6,
                hops=0,
                xid=discover.xid,
                secs=0,
                flags=0,
                ciaddr=offer.yiaddr,
                yiaddr=ipaddress.IPv4Address(0),
                siaddr=offer.siaddr,
                giaddr=ipaddress.IPv4Address(0),
                chaddr=MAC_ADDRESS,
                sname=b'',
                file=b'',
                options=dhcppython.options.OptionList(
                    [
                        dhcppython.options.options.short_value_to_object(53, 'DHCPREQUEST'),
                        dhcppython.options.options.short_value_to_object(50, offer.yiaddr),
                        dhcppython.options.options.short_value_to_object(54, offer.siaddr)
                    ])
            )
            client_socket.sendto(request.asbytes, ('<broadcast>', 67))

            ack, _ = client_socket.recvfrom(MAX_MSG_SIZE)
            ack = dhcppython.packet.DHCPPacket.from_bytes(ack)
            if ack.xid == discover.xid and ack.options.by_code(53).data == b'\x05':
                GOT_IP = True
                CLIENT_IP = ack.yiaddr
                LEASE_TIME = ack.options.by_code(51).value['lease_time']

            print(f'Got ip address {CLIENT_IP} from server with ip address {ack.siaddr} for {LEASE_TIME} secs...')
            break

    except Exception as e:
        print(e)
        time_out_interval = discover_timeout(time_out_interval)
        signal.alarm(int(time_out_interval))
