from UDP.initialConnection import udpConnectionHelper
from HTTP.announceConnection import httpAnnounceHelper
from UDP.announceConnection import udpAnnounceHelper
from twisted.internet import reactor, protocol
from bcoding import bencode, bdecode
from metaparser import MetaContent
from UDP.sender import Sender
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
    def __init__(self, meta_file, extra_trackers = False):
        # make sure the argument is correct
        if type(meta_file) != MetaContent:
            raise Exception('meta_file must be of type MetaContent')
        
        # Kind of waste of time rn
        self.trackers = []
        self.load_extra_trackers = extra_trackers
        if extra_trackers:
            self.extra_trackers()

        self.mf = meta_file
        self.generate_peer_id()

    def extra_trackers(self):
        trackers_file = open('trackers.txt', 'r')
        for t in trackers_file.readlines():
            self.trackers.append(urllib.parse.urlparse(t))

    '''
        Generates the peer id for the client, should only be 
        called once when the client starts
    '''
    def generate_peer_id(self):
        client_id = '-Bs' #Boris Skurikhin (2 bytes)
        client_version = '0001-' # (4 bytes) TODO: version control?
        rand = ''.join(random.choice(string.ascii_letters) for _ in range(20 - 8))
        
        self.peer_id = str(client_id + client_version + rand).encode()
        assert len(self.peer_id) == 20, 'Something broke while generating peer id'

    '''
        If the tracker type is UDP

    '''
    def udp_request(self):
        #https://libtorrent.org/udp_tracker_protocol.html
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(4)

        if not self.load_extra_trackers:
            self.trackers.append(self.mf.announce)

        # List of peers
        self.peers = []

        # Contact every tracker
        for announce in self.trackers:
            # We only care about UDP
            if announce.scheme != 'udp': 
                continue
            
            print('Querying', announce.hostname)

            # Establishing a connection with the UDP Server
            con_helper = udpConnectionHelper()
            ann_helper = udpAnnounceHelper()
            
            sender = Sender()

            try:
                # Create address to where we will be sending our packet
                address = (socket.gethostbyname(announce.hostname), announce.port)
            except Exception as e:
                continue

            # Pass off the request to the sender, receive bytes
            conn_response_bytes = sender.send_packet(sock, address, con_helper.pack_payload())
            
            # Move on from this tracker..
            if len(conn_response_bytes) == 0:
                continue

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

            # self.interval = ann_response['interval'] # no one gives a shit
            self.peers.extend(ann_response['peers']) #what we all came here for

    '''
        If the tracker type is HTTP
    '''
    def http_request(self):
        
        conn_helper = httpAnnounceHelper()

        params = {
            'info_hash': self.mf.info_hash,
            'peer_id': self.peer_id,
            'left': self.mf.length,
            'announce': self.mf.announce
        }

        raw_resp = conn_helper.pack_request(params)
        resp = conn_helper.unpack_request(raw_resp)
    
        exit(0)

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