import sys
import os
import tqdm
import select
import socket

CHUNK_SIZE = 1024


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    UNDERLINE = '\033[4m'


class Client:
    def __init__(self, host, port):
        self.sock = ''
        self.host = host
        self.port = port

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host, self.port))
            self.sock = sock
        except:
            raise ConnectionError(f'{Colors.FAIL}Cannot connect to {self.host} on port {self.port}') from None 

    def close(self):
        if self.sock:
            self.sock.close()    
        
    def sendall(self, message):
        if not self.sock:
            self.connect()
        
        self.sock.sendall(message.encode())

    def sendfile(self, filename):
        with open(filename, 'rb') as f:
            while True:

                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break

                self.sendall(chunk)

    def recvall(self):
        chunks = bytearray()

        while True:
            readable = select.select([self.sock], [], [], 2)
            if readable[0]:
                chunks.extend(self.sock.recv(CHUNK_SIZE))
            else:
                break      
        return chunks

def find_open_ports(host, r):
    open_ports = []
    start, end = r
    for port in range(start, end):
        with socket.socket() as sock:
            sock.settimeout(1)
            try:
                sock.connect((host, port))
                open_ports.append(port)
            except:
                pass    
             
    return open_ports

def main():
    '''
    Checking arguments
    '''
    if len(sys.argv) < 3:
        print(f'{Colors.FAIL}Invalid input...')
        return
    if not sys.argv[2].isdigit():
        print(f'{Colors.FAIL}Port shall be a number...')
        return
    
    client = Client(sys.argv[1], int(sys.argv[2]))
    try:
        client.connect()
        print(f'{Colors.CYAN}Connected to {sys.argv[1]} on port {sys.argv[2]}')
    except Exception as e:
        print(e)  
    
    while True:
        msg = ''
        while (next := input()) != 'send':
            msg += next + '\r\n'
        if msg.strip() == 'quit':
            break    
        client.sendall(msg)
        response = client.recvall()
        if response:
            print(f'{Colors.BLUE}{response.decode()}{Colors.CYAN}')


      
    
    
if __name__ == '__main__':
    main()