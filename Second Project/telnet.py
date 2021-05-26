import os
import sys
import ssl
import time
import select
import socket
import threading

CHUNK_SIZE = 1024
FILE_NAME_LENGTH = 256

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    UNDERLINE = '\033[4m'

def port_is_open(host, port):
    with socket.socket() as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            return True
        except:
            return False 

def open_ports(host, r):
    open_ports = []
    start, end = r
    for port in range(start, end):
        if port_is_open(host, port):
            open_ports.append(port) 
             
    return open_ports

class Peer:

    class Client(threading.Thread):
        def __init__(self, host, port):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.host = host
            self.port = port
        
        def run(self):
            try:
                self.sock.connect((self.host, self.port))
                print(f'{Colors.CYAN}Connected to {self.host} on port {self.port}')
            except:
                raise ConnectionError(f'{Colors.FAIL}Cannot connect to {self.host} on port {self.port}') from None

        def close(self):
            self.sock.close()  
    
    class Server(threading.Thread):
        def __init__(self, host):
            threading.Thread.__init__(self)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        def run(self):
            import random
            self.port = random.randrange(10000, 55000)
            while True:
                try:
                    self.sock.bind(('', self.port))
                    self.sock.listen()
                    print(f'{Colors.CYAN}Server is listening to port {self.port}')
                    break
                except:
                    self.port = random.randrange(10000, 55000)

            sock, address = self.sock.accept()
            print(f'{Colors.WARNING}{address} connected...')
            

        def close(self):
            self.sock.close()

    def __init__(self, host, port):
        self.server = self.Server(host)
        self.client = self.Client(host, port)

        self.server.start() 


def sendall(sock, message):
    sock.sendall(message)

def sendfile(sock, filename):
    with open(filename, 'rb') as f:
        data = f.read()

        print(filename.encode() + b' ' * (FILE_NAME_LENGTH - len(filename)))
        sendall(sock, filename.encode() + b' ' * (FILE_NAME_LENGTH - len(filename)))
        sendall(sock, data)

def recvall(sock):
    chunks = bytearray()
    while True:
        readable = select.select([sock], [], [], 1)
        if readable[0]:
            chunks.extend(sock.recv(CHUNK_SIZE))
        else:
            break
    return chunks    

def recvfile(sock):
    filename = sock.recv(FILE_NAME_LENGTH).decode().strip()
    data = recvall(sock)
    with open('Downloaded ' + filename, 'wb') as f:
        f.write(data)

def main():
    
    peer = Peer(host=sys.argv[1], port=int(sys.argv[2]))

    time.sleep(0.5)
    port = int(input(f'{Colors.GREEN}Host port> '))
    
    peer.client.port = port
    peer.client.start()

    while True:
        msg = ''
        while (next := input()) != 'send':
            msg += next + '\n'
        if msg.strip() == 'quit':
            break    
        sendall(peer.client.sock, msg.encode())
        # TODO
        response = recvall(peer.client.sock)
        if response:
            print(f'{Colors.BLUE}***Response***\n{response.decode()}{Colors.CYAN}')


if __name__ == '__main__':
    main()