from UDP.initialConnection import udpConnectionHelper
from UDP.announceConnection import udpAnnounceHelper
from UDP.sender import Sender
from twisted.internet import reactor, protocol
from metaparser import MetaContent
import urllib.parse
import requests
import socket
import random
import string

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
        client_id = '-Bs' #Boris Skurikhin (2 bytes)
        client_version = '0001-' # (4 bytes) TODO: version control?
        rand = ''.join(random.choice(string.ascii_letters) for _ in range(20 - 8))
        
        raw_id = client_id + client_version + rand
        self.peer_id = ''

        for i in range(0, 20):
            self.peer_id += format(ord(raw_id[i]), 'x')
        
        assert len(self.peer_id) == 40, 'Something broke while generating peer id'

    '''
        If the tracker type is UDP

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
        ann_helper = udpAnnounceHelper()
        sender = Sender()

        # Create address to where we will be sending our packet
        address = (socket.gethostbyname(self.mf.announce.hostname), self.mf.announce.port)

        # Pass off the request to the sender, receive bytes
        conn_response_bytes = sender.send_packet(sock, address, con_helper.pack_payload())
        conn_response = con_helper.unpack_payload(conn_response_bytes)

        # Parameters needed to send the announce payload
        params = {
            'conn_id': conn_response['conn_id'],
            'info_hash': self.mf.info_hash,
            'peer_id': self.peer_id,
            'left': self.mf.length
        }

        # Sends out another packet requesting a list of peers who have our file
        ann_response_bytes = sender.send_packet(sock, address, ann_helper.pack_payload(params))
        ann_response = ann_helper.unpack_payload(ann_response_bytes)

        self.interval = ann_response['interval']
        self.peers = ann_response['peers'] #what we all came here for

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

        # get peers depending on the tracker type
        if scheme == 'udp': self.udp_request()
        elif scheme == 'http': self.http_request()
        else: raise Exception('Unknown Scheme: %s' % scheme)

        return self.peers