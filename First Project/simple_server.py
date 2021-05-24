import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.bind(('', 8080))

while True:
    message, address = s.recvfrom(4096)
    print('GOT ' + '\"' + message.decode('utf-8') + '\" FROM ' + address[0])
