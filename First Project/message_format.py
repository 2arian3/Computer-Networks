import binascii


class Message:
    TYPES = {
        1: 'A',
        2: 'NS',
        5: 'CNAME',
        28: 'AAAA'
    }

    def __init__(self, msg):
        import random
        self.header = {
            'ID': random.randint(0, 65_535),
            'QR': 0,
            'OPCODE': 0,
            'AA': 0,
            'TC': 0,
            'RD': 1,
            'RA': 1,
            'Z': 0,
            'RCODE': 0,
            'QDCOUNT': 1,
            'ANCOUNT': 0,
            'NSCOUNT': 0,
            'ARCOUNT': 0
        }
        self.question = {
            'QNAME': '',
            'QTYPE': 1,
            'QCLASS': 1
        }
        self.answers = []
        self.authorities = []
        self.additional = []
        self.msg = msg

    def get_encoded_request(self):
        query_parameters = str(self.header['QR'])
        query_parameters += '{:04b}'.format(self.header['OPCODE'])
        query_parameters += str(self.header['AA'])
        query_parameters += str(self.header['TC'])
        query_parameters += str(self.header['RD'])
        query_parameters += str(self.header['RA'])
        query_parameters += str(self.header['Z']).zfill(3)
        query_parameters += str(self.header['RCODE']).zfill(4)
        query_parameters = '{:04x}'.format(int(query_parameters, 2))

        header = '{:04x}'.format(self.header['ID'])
        header += query_parameters
        header += '{:04x}'.format(self.header['QDCOUNT'])
        header += '{:04x}'.format(self.header['ANCOUNT'])
        header += '{:04x}'.format(self.header['NSCOUNT'])
        header += '{:04x}'.format(self.header['ARCOUNT'])

        for component in self.msg.split('.'):
            length = '{:02x}'.format(len(component))
            part = binascii.hexlify(component.encode()).decode()
            self.question['QNAME'] += length + part
        self.question['QNAME'] += '00'

        question = self.question['QNAME']
        question += '{:04x}'.format(self.question['QTYPE'])
        question += '{:04x}'.format(self.question['QCLASS'])

        return header + question

    def set_message_type(self, msg_type=1):
        if isinstance(msg_type, str):
            if msg_type in Message.TYPES.values():
                reverse = {k: v for v, k in Message.TYPES.items()}
                self.question['QTYPE'] = reverse[msg_type]
            else:
                self.question['QTYPE'] = 1
        elif isinstance(msg_type, int):
            if msg_type in Message.TYPES.values():
                self.question['QTYPE'] = msg_type
            else:
                self.question['QTYPE'] = 1

    def parser(self, index):
        parts = []
        while self.msg[index:index+2] != '00':
            length = int(self.msg[index:index + 2], 16)
            if 0b11000000 & length == 0b11000000:
                index = 2 * (int(self.msg[index:index+4], 16) & 0b0011111111111111)  # Finding compression offset
            else:
                parts.append(self.msg[index+2:index+length*2+2])
                index += length*2 + 2
        return parts

    def parse_rdata(self, index):
        answer = {}
        answer['NAME'] = self.msg[index:index + 4]
        answer['TYPE'] = int(self.msg[index + 4:index + 8], 16)
        answer['CLASS'] = int(self.msg[index + 8:index + 12], 16)
        answer['TTL'] = int(self.msg[index + 12:index + 20], 16)
        answer['RDLENGTH'] = int(self.msg[index + 20:index + 24], 16)

        index += 24
        if answer['CLASS'] == 1:  # IN class
            record_type = answer['TYPE']
            if record_type == 1:  # A record type
                octets = [self.msg[index+i:index+i+2] for i in range(0, 2 * answer['RDLENGTH'], 2)]
                answer['RDATA'] = '.'.join(list(map(lambda x: str(int(x, 16)), octets)))
            elif record_type in [2, 5]:  # CNAME and NS record type
                parts = self.parser(index)
                answer['RDATA'] = '.'.join(list(map(lambda x: binascii.unhexlify(x).decode(), parts)))
            elif record_type == 28:  # AAAA record type
                octets = [self.msg[index + i:index + i + 4] for i in range(0, 2 * answer['RDLENGTH'], 4)]
                for i in range(len(octets)):
                    octet = list(octets[i])
                    while len(octet) and octet[0] == '0':
                        octet.pop(0)
                    if not len(octet):
                        octets[i] = '0'
                    else:
                        octets[i] = ''.join(octet)
                result = []
                for octet in octets:
                    if octet == '0':
                        if len(result) == 0 or result[-1] != '':
                            result.append('')
                    else:
                        result.append(octet)
                answer['RDATA'] = ':'.join(result)
            index += 2 * answer['RDLENGTH']
        return answer, index


def get_decoded_message(msg):
    message = Message(msg=msg)
    message.header['ID'] = msg[:4]
    message.header['QDCOUNT'] = msg[8:12]
    message.header['ANCOUNT'] = msg[12:16]
    message.header['NSCOUNT'] = msg[16:20]
    message.header['ARCOUNT'] = msg[20:24]

    query_flags = '{:b}'.format(int(msg[4:8], 16)).zfill(16)
    message.header['QR'] = query_flags[:1]
    message.header['OPCODE'] = query_flags[1:5]
    message.header['AA'] = query_flags[5:6]
    message.header['TC'] = query_flags[6:7]
    message.header['RD'] = query_flags[7:8]
    message.header['RA'] = query_flags[8:9]
    message.header['Z'] = query_flags[9:12]
    message.header['RCODE'] = query_flags[12:16]

    parts = message.parser(24)
    index = 26 + sum(map(len, parts)) + 2*len(parts)

    message.question['QNAME'] = '.'.join(list(map(lambda x: binascii.unhexlify(x).decode(), parts)))
    message.question['QTYPE'] = int(msg[index:index + 4], 16)
    message.question['QCLASS'] = int(msg[index + 4:index + 8], 16)
    index += 8

    number_of_answers = int(message.header['ANCOUNT'], 16)
    number_of_authority_records = int(message.header['NSCOUNT'], 16)
    number_of_additional_records = int(message.header['ARCOUNT'], 16)

    for _ in range(number_of_answers):
        answer, index = message.parse_rdata(index)
        if 'RDATA' in answer:
            message.answers.append(answer)

    for _ in range(number_of_authority_records):
        answer, index = message.parse_rdata(index)
        if 'RDATA' in answer:
            message.authorities.append(answer)

    for _ in range(number_of_additional_records):
        answer, index = message.parse_rdata(index)
        if 'RDATA' in answer:
            message.additional.append(answer)

    return message
