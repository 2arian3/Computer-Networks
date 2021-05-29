import enum
import select
import socket
import mysql.connector

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
    filename = sock.recv(FILE_NAME_LENGTH).decode().strip().split('/')[-1]
    data = recvall(sock)
    with open('Downloaded ' + filename, 'wb') as f:
        f.write(data)
    return 'Downloaded ' + filename

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

def connect_to_db():
    mydb = mysql.connector.connect(
        host='localhost',
        user='root',
        password='********',
        database='Telnet',
        port='****'
    )
    return mydb

def insert_into_db(db, command, host, port, result):
    cursor = db.cursor()
    sql = 'INSERT INTO history (command, host, port, result) VALUES (%s, %s, %s, %s)'
    cursor.execute(sql, (command, host, port, result))
    db.commit()

def see_history(db, host, port):
    cursor = db.cursor()
    sql = 'SELECT command, result FROM history WHERE host = %s AND port = %s'
    cursor.execute(sql, (host, port,))
    results = cursor.fetchall()

    for i in range(len(results)):
        print(f'{Colors.FAIL}[{i+1}] {Colors.CYAN}Command: {results[i][0]}\tResult: {results[i][1]}')