import os
import sys
import ssl
import select
import socket
import threading

MESSAGE_SIZE = 128

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

    class Client:
        def __init__(self, host, port):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.host = host
            self.port = port
        
        def connect(self):
            try:
                self.sock.connect((self.host, self.port))
                print(f'{Colors.CYAN}Connected to {self.host} on port {self.port}')
            except:
                raise ConnectionError(f'{Colors.FAIL}Cannot connect to {self.host} on port {self.port}') from None

        def close(self):
            self.sock.close()  
    
    class Server(threading.Thread):
        def __init__(self, host):
            import random
            threading.Thread.__init__(self)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.host = host
            self.port = random.randrange(53000, 53500)

        def run(self):
            try:
                self.sock.bind((self.host, self.port))
                self.sock.listen()
                print(f'{Colors.CYAN}Server is listening to port {self.port}')
            except:
                raise ConnectionError(f'{Colors.FAIL}Cannot bind to port {self.port}') from None 
            while True:
                # TODO
                sock, address = self.sock.accept()
                print(f'{Colors.WARNING}{address[0]} connected...')
                threading.Thread(target=handle, args=(sock, address)).start()

        def close(self):
            self.sock.close()

    def __init__(self, host, port):
        self.server = self.Server(host)
        self.client = self.Client(host, port)

        self.server.start()
        #self.client.connect()  


def sendall(sock, message):
    if type(message) == str:
        message = message.encode()

    message_length = str(len(message)).encode()
    message_length += b' ' * (MESSAGE_SIZE - len(message_length))

    sock.send(message_length)       
    sock.send(message)

def readfile(filename):
    with open(filename, 'rb') as f:
        return f.read()

def recvall(sock):
    message_length = int(sock.recv(MESSAGE_SIZE).decode().strip())
    return sock.recv(message_length)

def handle(sock, address):
    while (message := recvall(sock).decode()) != 'Quit':
        print(f'{Colors.BLUE}Got \'{message}\' from client')
        sendall(sock, input('\nMessage> '))

def main():
    try:
        peer = Peer(host=sys.argv[1], port=int(sys.argv[2]))
    except Exception as e:
        print(e)
        return
    
    port = int(input('Host port> '))
    peer.client.port = port
    peer.client.connect()

    while True:
        msg = ''
        while (next := input()) != 'send':
            msg += next + '\n'
        if msg.strip() == 'quit':
            break    
        sendall(peer.client.sock, msg)
        # TODO
        response = recvall()
        if response:
            print(f'{Colors.BLUE}***Response***\n{response.decode()}{Colors.CYAN}')


if __name__ == '__main__':
    main()