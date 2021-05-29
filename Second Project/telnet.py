import os
import sys
import ssl
import time
import threading
from utils import *

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
                            print(f'\n{Colors.WARNING}message> {Colors.BLUE}{msg}')
                            sock.sendall(b'Got your encrypted message...')

                elif command == 'UPLOAD':
                    recvfile(self.sock)
                    sendall(self.sock, b'Got the file...')
                    print(f'\n{Colors.WARNING}ack>{Colors.BLUE} Downloaded the file from server')

                elif command == 'EXEC':
                    cmd = recvall(self.sock).decode()
                    sendall(self.sock, os.popen(cmd).read().encode())
                    print(f'\n{Colors.WARNING}executed>{Colors.BLUE} {cmd}')

                print(f'\n{Colors.WARNING}telnet>{Colors.BLUE} ', end='')
                

        def close(self):
            self.sock.close() 
    
    class Server(threading.Thread):
        def __init__(self, server_port):
            threading.Thread.__init__(self)
            self._db = connect_to_db()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.port = server_port

        def run(self):
            while True:
                try:
                    self.sock.bind(('', int(self.port)))
                    self.sock.listen()
                    print(f'\n{Colors.CYAN}Server is listening to port {self.port}')
                    break
                except:
                    self.port = input(f'\n{Colors.FAIL}Server cannot bind to port {self.port}...\nEnter another port>')
                
            
            sock, _ = self.sock.accept()
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
                                print(f'\n{Colors.WARNING}response> {Colors.BLUE}{response}')
                        insert_into_db(self._db, ' '.join(command), 'localhost', self.port, response)
                        
                    
                    elif len(command) > 2 and command[1] == 'send':
                        sendall(sock, str(FUNCTIONS.SEND.value).encode())
                        sendall(sock, ' '.join(command[2:]).encode())
                        time.sleep(0.5)
                        response = recvall(sock).decode()
                        print(f'\n{Colors.WARNING}reponse>{Colors.BLUE} {response}')
                        insert_into_db(self._db, ' '.join(command), 'localhost', self.port, response)


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
                            insert_into_db(self._db, ' '.join(command), 'localhost', self.port, response)
                        except:
                            print(f'\n{Colors.FAIL}INVALID PATH...') 

                    elif len(command) > 2 and command[1] == 'exec':
                        sendall(sock, str(FUNCTIONS.EXEC.value).encode())
                        sendall(sock, ' '.join(command[2:]).encode())
                        time.sleep(0.5)
                        response = recvall(sock).decode()
                        print(f'\n{Colors.WARNING}response>{Colors.BLUE} {response}')
                        insert_into_db(self._db, ' '.join(command), 'localhost', self.port, response)

                    elif command[1] == 'history':
                        see_history(self._db, 'localhost', self.port)

        def close(self):
            self.sock.close()

    def __init__(self, key_file, certificate_file, host, server_port):
        self.server = self.Server(server_port)
        self.client = self.Client(host, key_file, certificate_file)    

def main():
    if len(sys.argv) < 5:
        print(f'{Colors.FAIL}NOT ENOUGH ARGUMENTS...\npython3 telnet.py host server_port key_file cert_file')
        return

    try:
        with open(sys.argv[3], 'rb') as f:
            pass
    except:
        print(f'{Colors.FAIL}File {sys.argv[3]} does not exist...')
        return

    try:
        with open(sys.argv[4], 'rb') as f:
            pass
    except:
        print(f'{Colors.FAIL}File {sys.argv[4]} does not exist...')
        return
    
    if not sys.argv[2].isdigit():
        print(f'{Colors.FAIL}INVALID PORT NUMBER...')
        return

    host, server_port = sys.argv[1], int(sys.argv[2])
    key_file, certificate_file = sys.argv[3], sys.argv[4]
    peer = Peer(key_file, certificate_file, host, server_port)
    peer.server.start()

    time.sleep(0.5)
    port = int(input(f'\n{Colors.GREEN}Host port> '))
    
    peer.client.port = port
    peer.client.start()


if __name__ == '__main__':
    main()