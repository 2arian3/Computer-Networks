import sys
import select
import socket

CHUNK_SIZE = 1024

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
            raise ConnectionError('Cannot connect to {} on port {}'.format(self.host, self.port)) from None 

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
    client = Client('www.google.com', 80)
    
    
    
if __name__ == '__main__':
    main()