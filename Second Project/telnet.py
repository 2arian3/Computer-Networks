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
FUNCTIONS = enum.Enum('FUNCTIONS', 'SEND SENDENC UPLOAD EXEC HIST')

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

def open_ports(hosts=['aut.ac.ir'], r=(80, 90)):
    open_ports = {}
    start, end = r
    for host in hosts:
        open_ports[host] = []
        for port in range(start, end):
            if port_is_open(host, port):
                open_ports[host].append(port) 
             
    return open_ports

class Peer:

    class Client(threading.Thread):
        def __init__(self, host, key_file, certificate_file):
            threading.Thread.__init__(self)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.host = host
            self.port = ''
            self.key_file = key_file
            self.certificate_file = certificate_file
        
        def run(self):
            try:
                self.sock.connect((self.host, self.port))
                print(f'\n{Colors.CYAN}Connected to {self.host} on port {self.port}')
            except:
                raise ConnectionError(f'\n{Colors.FAIL}Cannot connect to {self.host} on port {self.port}') from None

            running = True
            while running:
                command = FUNCTIONS(int(self.sock.recv(1).decode())).name
                if command == 'SEND':
                    message = recvall(self.sock).decode()
                    sendall(self.sock, b'Got your message...')
                    print(f'\n{Colors.WARNING}message>{Colors.BLUE} {message}')

                elif command == 'SENDENC':
                    sendfile(self.sock, self.certificate_file)
                    time.sleep(0.5)
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(self.certificate_file, self.key_file)
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        server.bind(('', 8383))
                        server.listen()
                        with context.wrap_socket(server, server_side=True) as tls:
                            sock, _ = tls.accept()
                            msg = sock.recv(CHUNK_SIZE).decode()
                            print(f'{Colors.WARNING}message> {Colors.BLUE}{msg}')
                            sock.sendall(b'Got your encrypted message...')

                elif command == 'UPLOAD':
                    recvfile(self.sock)
                    sendall(self.sock, b'Got the file...')
                    print(f'\n{Colors.WARNING}ack>{Colors.BLUE} Downloaded the file from server')

                elif command == 'EXEC':
                    cmd = recvall(self.sock).decode()
                    sendall(self.sock, os.popen(cmd).read().encode())
                    print(f'\n{Colors.WARNING}executed>{Colors.BLUE} {cmd}')
                

        def close(self):
            self.sock.close() 
    
    class Server(threading.Thread):
        def __init__(self, key_file, certificate_file):
            threading.Thread.__init__(self)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.history = []
            self.key_file = key_file
            self.certificate_file = certificate_file

        def run(self):
            import random
            self.port = random.randrange(10000, 55000)
            while True:
                try:
                    self.sock.bind(('', self.port))
                    self.sock.listen()
                    print(f'\n{Colors.CYAN}Server is listening to port {self.port}')
                    break
                except:
                    self.port = random.randrange(10000, 55000)

            sock, address = self.sock.accept()
            print(f'\n{Colors.WARNING}{address} connected...')

            running = True
            while running:
                command = input(f'\n{Colors.WARNING}telnet>{Colors.BLUE} ').split()
                if command[0] == 'telnet' and len(command) >= 2:
                    if len(command) > 3 and ' '.join(command[1:3]) == 'send -e':
                        '''
                        Using ssl to send encrypted message
                        '''
                        sendall(sock, str(FUNCTIONS.SENDENC.value).encode())
                        filename = recvfile(sock)
                        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                        context.load_verify_locations(filename)
                        server_hostname = ''
                        for t in context.get_ca_certs()[0]['subject']:
                            if t[0][0] == 'commonName':
                                server_hostname = t[0][1]
                                break
                        '''
                        8383 is the supposed secure port on the local computer
                        '''
                        with socket.create_connection(('', 8383)) as client:
                            with context.wrap_socket(client, server_hostname=server_hostname) as tls:
                                tls.sendall(' '.join(command[3:]).encode())
                                response = tls.recv(CHUNK_SIZE).decode()
                                print(f'{Colors.WARNING}response> {Colors.BLUE}{response}')
                        self.history.append(' '.join(command))
                    
                    elif len(command) > 2 and command[1] == 'send':
                        sendall(sock, str(FUNCTIONS.SEND.value).encode())
                        sendall(sock, ' '.join(command[2:]).encode())
                        time.sleep(0.5)
                        response = recvall(sock).decode()
                        print(f'\n{Colors.WARNING}reponse>{Colors.BLUE} {response}')
                        self.history.append(' '.join(command))

                    elif len(command) > 2 and command[1] == 'upload':
                        path = command[2].split('/')
                        current_path = os.getcwd()
                        
                        try:
                            if len(path) > 1:
                                os.chdir('/'.join(path[:-1]))
                            sendall(sock, str(FUNCTIONS.UPLOAD.value).encode())
                            sendfile(sock, path[-1])
                            os.chdir(current_path)
                            time.sleep(0.5)
                            response = recvall(sock).decode()
                            print(f'\n{Colors.WARNING}response>{Colors.BLUE} {response}') 
                            self.history.append(' '.join(command))
                        except:
                            print(f'\n{Colors.FAIL}INVALID PATH...') 

                    elif len(command) > 2 and command[1] == 'exec':
                        sendall(sock, str(FUNCTIONS.EXEC.value).encode())
                        sendall(sock, ' '.join(command[2:]).encode())
                        time.sleep(0.5)
                        response = recvall(sock).decode()
                        print(f'\n{Colors.WARNING}response>{Colors.BLUE} {response}')
                        self.history.append(' '.join(command))

                    elif command[1] == 'history':
                        for i in range(len(self.history)):
                            print(f'{Colors.FAIL}[{i}] {Colors.CYAN}{self.history[i]}')

        def close(self):
            self.sock.close()

    def __init__(self, key_file, certificate_file, host):
        self.server = self.Server(key_file, certificate_file)
        self.client = self.Client(host, key_file, certificate_file)


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
    '''
    First things first recieve the file name.
    Then just recieve the file chunks one by one and write it into a file. 
    '''
    filename = sock.recv(FILE_NAME_LENGTH).decode().strip()
    data = recvall(sock)
    with open('Downloaded ' + filename, 'wb') as f:
        f.write(data)
    return 'Downloaded ' + filename    

def main():

    host = sys.argv[1]
    key_file, certificate_file = map(str, input(f'{Colors.WARNING}Please enter key file and certificate file names...{Colors.BLUE}').split())
    peer = Peer(key_file, certificate_file, host)
    peer.server.start()

    time.sleep(0.5)
    port = int(input(f'\n{Colors.GREEN}Host port> '))
    
    peer.client.port = port
    peer.client.start()


if __name__ == '__main__':
    main()