import csv
import socket
import pickle
from message_format import *

servers = {
    'Iterative': '199.7.91.13',
    'Recursive': '8.8.8.8'
}


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    UNDERLINE = '\033[4m'


def send_request(server_ip='8.8.8.8', msg=''):
    port = 53
    server_address = (server_ip, port)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.sendto(binascii.unhexlify(msg), server_address)
            res, _ = s.recvfrom(4096)
            return binascii.hexlify(res).decode('utf-8')
        except Exception as e:
            print(e)


def encode_message(msg, msg_type='A'):
    msg = Message(msg)
    msg.set_message_type(msg_type=msg_type)
    return msg.get_encoded_request()


def request(message, record, server_ip):
    msg = encode_message(msg=message, msg_type=record)
    response = send_request(server_ip=server_ip, msg=msg)
    return get_decoded_message(response)


def handle_queries(address, record, server):
    response = request(address, record, server)
    if response.answers:
        return response
    print(f'\n{Colors.WARNING}Response from {server}')
    show_result(response)
    if response.additional:
        for add in response.additional:
            if add['TYPE'] == 1:  # A type
                additional_response = handle_queries(address, record, add['RDATA'])
                if additional_response:
                    return additional_response
    return None


def get_type(option=''):
    mapping = {'1': 'A', '2': 'AAAA', '3': 'CNAME'}
    print(f'\n{Colors.GREEN}Choose one of the record types below{option}!')
    print(f'{Colors.HEADER}[1] {Colors.BLUE}A')
    print(f'{Colors.HEADER}[2] {Colors.BLUE}AAAA')
    print(f'{Colors.HEADER}[3] {Colors.BLUE}CNAME')
    t = input()
    if t not in mapping:
        print(f'{Colors.FAIL}Wrong Input!')
        return get_type(option)
    return mapping[t]


def get_query_type(option=''):
    mapping = {'1': 'Recursive', '2': 'Iterative'}
    print(f'\n{Colors.GREEN}Choose the query type{option}!')
    print(f'{Colors.HEADER}[1] {Colors.BLUE}Recursive')
    print(f'{Colors.HEADER}[2] {Colors.BLUE}Iterative')
    t = input()
    if t not in mapping:
        print(f'{Colors.FAIL}Wrong Input!')
        return get_query_type(option)
    return mapping[t]


def check_and_modify_cached(cache, name, record):
    if name in cache and record in cache[name]:
        cache[name][record]['count'] += 1
        if cache[name][record]['count'] >= 4 and cache[name][record]['result']:
            return cache[name][record]['result']
        else:
            return None

    if name not in cache:
        cache[name] = dict()

    if record not in cache[name]:
        cache[name][record] = dict()
        cache[name][record]['count'] = 1
        cache[name][record]['result'] = ''
        return None

    return None


def pre_processing(cache, name):
    query = get_query_type(' for {}'.format(name))
    record = get_type(' for {}'.format(name))
    return check_and_modify_cached(cache, name, record), record, query


def show_result(res):
    header = res.header
    question = res.question
    answers = res.answers
    authorities = res.authorities
    additional = res.additional

    def show_response(ans):
        print('{}NAME: {}{}'.format(Colors.HEADER, Colors.CYAN, ans['NAME']))
        print('{}TYPE: {}{}'.format(Colors.HEADER, Colors.CYAN, ans['TYPE']))
        print('{}CLASS: {}{}'.format(Colors.HEADER, Colors.CYAN, ans['CLASS']))
        print('{}TTL: {}{}'.format(Colors.HEADER, Colors.CYAN, ans['TTL']))
        print('{}RDLENGTH: {}{}'.format(Colors.HEADER, Colors.CYAN, ans['RDLENGTH']))
        print('{}RDATA: {}{}\n'.format(Colors.HEADER, Colors.CYAN, ans['RDATA']))

    print('{}Message Header'.format(Colors.HEADER))
    print('{}ID: {}{}'.format(Colors.HEADER, Colors.CYAN, header['ID']))
    print('{}QR: {}{}'.format(Colors.HEADER, Colors.CYAN, header['QR']))
    print('{}OPCODE: {}{}'.format(Colors.HEADER, Colors.CYAN, header['OPCODE']))
    print('{}AA: {}{}'.format(Colors.HEADER, Colors.CYAN, header['AA']))
    print('{}TC: {}{}'.format(Colors.HEADER, Colors.CYAN, header['TC']))
    print('{}RD: {}{}'.format(Colors.HEADER, Colors.CYAN, header['RD']))
    print('{}RA: {}{}'.format(Colors.HEADER, Colors.CYAN, header['RA']))
    print('{}Z: {}{}'.format(Colors.HEADER, Colors.CYAN, header['Z']))
    print('{}RCODE: {}{}'.format(Colors.HEADER, Colors.CYAN, header['RCODE']))
    print('{}QDCOUNT: {}{}'.format(Colors.HEADER, Colors.CYAN, header['QDCOUNT']))
    print('{}ANCOUNT: {}{}'.format(Colors.HEADER, Colors.CYAN, header['ANCOUNT']))
    print('{}NSCOUNT: {}{}'.format(Colors.HEADER, Colors.CYAN, header['NSCOUNT']))
    print('{}ARCOUNT: {}{}\n'.format(Colors.HEADER, Colors.CYAN, header['ARCOUNT']))

    print('{}Message Question'.format(Colors.HEADER))
    print('{}QNAME: {}{}'.format(Colors.HEADER, Colors.CYAN, question['QNAME']))
    print('{}QTYPE: {}{}'.format(Colors.HEADER, Colors.CYAN, question['QTYPE']))
    print('{}QCLASS: {}{}\n'.format(Colors.HEADER, Colors.CYAN, question['QCLASS']))

    if answers:
        print('{}Message Answer'.format(Colors.HEADER))
        for answer in answers:
            print('{}Answer {}'.format(Colors.CYAN, answers.index(answer)+1))
            show_response(answer)

    if authorities:
        print('{}Message Authority'.format(Colors.HEADER))
        for authority in authorities:
            print('{}Authority {}'.format(Colors.CYAN, authorities.index(authority)+1))
            show_response(authority)

    if additional:
        print('{}Message Additional'.format(Colors.HEADER))
        for add in additional:
            print('{}Additional {}'.format(Colors.CYAN, additional.index(add)+1))
            show_response(add)


'''
This is the implementation of the first bonus part.
To test this part, uncomment the following code. 

ip = '127.0.0.1'
port = 8080

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.sendto(b'Hey my server!', (ip, port))
    s.sendto(b'This is just a test.', (ip, port))
    s.sendto(b'Hopefully i can send you my messages!', (ip, port))
'''


def main():
    name_addresses = []
    with open('data.csv', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_file:
            name_addresses.append(row.replace('\n', ''))


    with open('cached.dns', 'rb') as cache_file:
        cached = pickle.load(cache_file)


    print(f'{Colors.HEADER}Hi!\nI\'m a simple program helping you out with DNS servers!')
    running = True
    while running:
        print(f'\n{Colors.GREEN}Choose one of the options below to start!')
        print(f'{Colors.HEADER}[1] {Colors.BLUE}Reading from data.csv!')
        print(f'{Colors.HEADER}[2] {Colors.BLUE}Entering request manually!')
        print(f'{Colors.HEADER}[3] {Colors.BLUE}Exit!')
        command = input()
        if command == '1':
            for name_address in name_addresses:

                result, record_type, query_type = pre_processing(cached, name_address)
                if result is None:
                    result = handle_queries(name_address, record_type, servers[query_type])
                    # changing cached data
                    if isinstance(result, Message) and result.header['ANCOUNT']:
                        cached[name_address][record_type]['result'] = result

                if isinstance(result, Message):
                    show_result(result)
            print(f'{Colors.HEADER}End of data.csv file!')

        elif command == '2':
            name_address = input(f'{Colors.BLUE}Please enter the name address!')
            result, record_type, query_type = pre_processing(cached, name_address)
            if result is None:
                result = handle_queries(name_address, record_type, servers[query_type])
                # changing cached data
                if isinstance(result, Message) and result.header['ANCOUNT']:
                    cached[name_address][record_type]['result'] = result

            if isinstance(result, Message):
                show_result(result)

        elif command == '3':
            running = False
        else:
            print(f'{Colors.FAIL}Wrong Input!')
    save = input(f'\n{Colors.HEADER}Do you want me to store the resolved IP\'s in output.csv?[y/n]')
    # saving data in output.csv
    if save == 'y':
        with open('output.csv', 'w', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=' ')

            csv_writer.writerow(['ADDRESS', 'TYPE', 'RESULT'])
            for name_address in cached:
                for record in cached[name_address]:
                    if isinstance(cached[name_address][record]['result'], Message):
                        for answer in cached[name_address][record]['result'].answers:
                            csv_writer.writerow([name_address, Message.TYPES[answer['TYPE']], answer['RDATA']])

    with open('cached.dns', 'wb') as cache_file:
        pickle.dump(cached, cache_file)


if __name__ == '__main__':
    main()