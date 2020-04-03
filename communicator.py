from metaparser import MetaContent
import urllib.parse
import requests
import socket
import random
import string
import struct

'''
    This class is responsible for HTTP communication
    with the tracker. Pretty straight forward stuff.
'''
class Communicator:
    def __init__(self, meta_file):
        # make sure the argument is correct
        if type(meta_file) != MetaContent:
            raise Exception('meta_file must be of type MetaContent')
        
        self.mf = meta_file
        self.generate_peer_id()

    '''
        Generates the peer id for the client, should only be 
        called once when the client starts
    '''
    def generate_peer_id(self):
        client_id = 'Bs' #Boris Skurikhin (2 bytes)
        client_version = '0001' # (4 bytes) TODO: version control?
        rand = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(14))
        self.peer_id = client_id + client_version + rand

    '''
        If the tracker type is UDP

        Useful information about integer data type:

        typedef signed char        int8_t;
        typedef short              int16_t;
        typedef int                int32_t;
        typedef long long          int64_t;
    '''
    def udp_request(self):
        # When we send params, they must be percent encoded:
        # https://en.wikipedia.org/wiki/Percent-encoding

        # url encode the hash_info string
        hash_info_bytes = bytearray.fromhex(self.mf.info_hash)
        hash_info_enc = urllib.parse.quote(hash_info_bytes)

        #https://libtorrent.org/udp_tracker_protocol.html
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(4)

        # connection packet we will be sending
        connection_id = 0x41727101980
        action = 0
        transaction_id = random.randint(1, 10000)

        a = struct.pack('>Q', connection_id)
        b = struct.pack('>I', action)
        c = struct.pack('>I', transaction_id)

        d = a + b + c

        host = socket.gethostbyname(self.mf.announce.hostname)
        port = int(self.mf.announce.port)
        
        send_address = (host, port)
        
        sock.sendto(d, send_address)

        r_message = b''
        
        while True:
            try:
                buff = sock.recv(4096)
                if len(buff) <= 0:
                    break
                r_message += buff
            except socket.error as e:
                print(e)
            except Exception as e:
                print(e)
        
        print(r_message)



    '''
        If the tracker type is HTTP
    '''
    def http_request(self):
        return None


    '''
        This function is responsible for 
        contacting the tracker and receiving a list
        of peers to download the file from
    '''
    def get_peers(self):
        scheme = self.mf.announce.scheme

        if scheme == 'udp':
            self.udp_request()
        elif scheme == 'http':
            self.http_request()
        else:
            raise Exception('%s scheme not supported!' % scheme)
        
        
        