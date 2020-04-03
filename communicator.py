from UDP.connection import udpConnectionHelper
from UDP.sender import Sender
from metaparser import MetaContent
import urllib.parse
import requests
import socket
import random
import string
import struct

'''
    This class is responsible for HTTP/UDP communication
    with the tracker. Pretty (not) straight forward stuff.
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

        # Establishing a connection with the UDP Server
        con_helper = udpConnectionHelper()
        sender = Sender()

        # Create address to where we will be sending our packet
        address = (socket.gethostbyname(self.mf.announce.hostname), self.mf.announce.port)

        # Pass off the request to the sender
        response = sender.send_packet(sock, address, con_helper.pack_payload(), 16, udpConnectionHelper)
    
        print(con_helper.transaction_id)
        print(con_helper.unpack_payload(response))

        # Send off the packet
        # sock.sendto(con_helper.pack_payload(), address)

        # try:
        #     # Attempt to receive 16 bytes back
        #     buffer = sock.recv(16)
        #     assert len(buffer) == 16, 'Received buffer was not 16 bytes'

        #     print(con_helper.unpack_payload(buffer))
        # except socket.error as e:
        #     print(e)




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

        if scheme == 'udp': self.udp_request()
        elif scheme == 'http': self.http_request()
        else: raise Exception('Unknown Scheme: %s' % scheme)
        
        
        