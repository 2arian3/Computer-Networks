import os
import sys
import ssl
import time
import enum
import select
import socket
import threading

CHUNK_SIZE = 1024
FILE_NAME_LENGTH = 256
FUNCTIONS = enum.Enum('FUNCTIONS', 'SEND SENDENC UPLOAD EXEC QUIT')

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
            threading.Thread.__init__(self)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.host = host
            self.port = port
        
        def run(self):
            try:
                self.sock.connect((self.host, self.port))
                print(f'{Colors.CYAN}Connected to {self.host} on port {self.port}')
            except:
                raise ConnectionError(f'{Colors.FAIL}Cannot connect to {self.host} on port {self.port}') from None

            running = True
            while running:
                command = FUNCTIONS(int(self.sock.recv(1).decode())).name
                if command == 'SEND':
                    message = recvall(self.sock).decode()
                    sendall(self.sock, b'Got your message...')
                    print(f'{Colors.WARNING}message>{Colors.BLUE} {message}')

                elif command == 'UPLOAD':
                    recvfile(self.sock)
                    sendall(self.sock, b'Got the file...')
                    print(f'{Colors.WARNING}ack>{Colors.BLUE} Downloaded the file from server')

                elif command == 'EXEC':
                    cmd = recvall(self.sock).decode()
                    sendall(self.sock, os.popen(cmd).read().encode())
                    print(f'{Colors.WARNING}executed>{Colors.BLUE} {cmd}')
                

        def close(self):
            self.sock.close()  
    
    class Server(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.history = []

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

            running = True
            while running:
                command = input(f'{Colors.WARNING}telnet>{Colors.BLUE} ').split()
                if command[0] == 'telnet' and len(command) >= 3:
                    if command[1] == 'send':
                        sendall(sock, str(FUNCTIONS.SEND.value).encode())
                        sendall(sock, ' '.join(command[2:]).encode())
                        time.sleep(0.5)
                        print(f'{Colors.WARNING}reponse>{Colors.BLUE} {recvall(sock)}')

                    elif len(command) > 3 and ' '.join(command[1:3]) == 'send -e':
                        # TODO
                        ...

                    elif command[1] == 'upload':
                        path = command[2].split('/')
                        current_path = os.getcwd()
                        
                        try:
                            if len(path) > 1:
                                os.chdir('/'.join(path[:-1]))
                            sendall(sock, str(FUNCTIONS.UPLOAD.value).encode())
                            sendfile(sock, path[-1])
                            os.chdir(current_path)
                            time.sleep(0.5)
                            print(f'{Colors.WARNING}reponse>{Colors.BLUE} {recvall(sock).decode()}') 
                        except:
                            print(f'{Colors.FAIL}INVALID PATH...') 

                    elif command[1] == 'exec':
                        sendall(sock, str(FUNCTIONS.EXEC.value).encode())
                        sendall(sock, ' '.join(command[2:]).encode())
                        time.sleep(0.5)
                        print(f'{Colors.WARNING}reponse>{Colors.BLUE} {recvall(sock).decode()}')

                self.history.append(' '.join(command))



        def close(self):
            self.sock.close()

    def __init__(self, host, port):
        self.server = self.Server()
        self.client = self.Client(host, port)


def sendall(sock, message):
    sock.sendall(message)

def sendfile(sock, filename):
    with open(filename, 'rb') as f:
        data = f.read()

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
    peer.server.start()

    time.sleep(0.5)
    port = int(input(f'{Colors.GREEN}Host port> '))
    
    peer.client.port = port
    peer.client.start()


if __name__ == '__main__':
    main()