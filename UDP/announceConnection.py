import random
import struct
import hashlib
import ipaddress

class udpAnnounceHelper:
    '''
        This is used with a UDP Tracker, upon
        the announce. This is kind of
        like a handshake.

        64 + 32 + 32 + 8[20] + 8[20] + 64 + 64 + 64 + 32 + u32 + u32 + 32 + u16 + u16
        =  8 + 4 + 4 + 20 + 20 + 8 + 8 + 8 + 4 + 4 + 4 + 4 + 2
        = 98 bytes (total packet size)
    '''
   
    # The thing that I kept messing up was the endian order
    # https://docs.python.org/2/library/struct.html

    '''
        Generates a pretty hefty announce payload to start 
        receiving a list of peers :)
    '''
    def pack_payload(self, params):
        self.transaction_id = random.randint(1, 100000)
        _info_hash = [] # temporary value to store individual bytes of the hash
        _peer_id = [] # temporary value to store individual bytes of the peer id

        # loops through the hash hex, and creates array of 2 byte integers
        for i in range(0, 40, 2):
            _info_hash.append(int(params['info_hash'][i : i + 2], 16))
            _peer_id.append(int(params['peer_id'][i : i + 2], 16))

        # unsigned bytes
        info_hash = struct.pack('>20B', *_info_hash)
        peer_id = struct.pack('>20B', *_peer_id)
        
        payload = struct.pack('>QII20B20BQQQIIIiH', *[
            params['conn_id'], # Q
            1, # I
            self.transaction_id, #I
            *_info_hash, #20B
            *_peer_id, #20B
            0, #Q
            0, #Q
            0, #Q
            0, #I
            0, #I
            0, #I
            -1, #i
            8000 #h
        ])

        assert(len(payload) == 98), 'Invalid payload length %d' % (len(payload)) 
        return payload
    
    '''
        action = 4 bytes, should be 1 
        trans_id = 4 bytes, should be the same
        interval = 4 bytes, # of seconds before next announce
        leechers = 4 bytes, # of leechers
        seeders = 4 bytes, # of seeders
        ---
        and then a list of peers 6 bytes per peer
    '''
    def unpack_payload(self, payload):
        hex_string = payload.hex()

        # extract stuff from the the payload
        action = int(hex_string[ : 8], 16)
        trans_id = int(hex_string[8 : 16], 16)
        interval = int(hex_string[16 : 24], 16)
        leechers = int(hex_string[24: 32], 16)
        seeders = int(hex_string[32:40], 16)

        assert action == 1, 'Action response did not match 1'
        assert trans_id == self.transaction_id, 'Transaction id didn\'t match'

        peers = []

        # Extract a list of peers
        for i in range(40, len(hex_string), 12):
            ip_add = str(ipaddress.IPv4Address(int(hex_string[i : i + 8], 16)))
            port = str(int(hex_string[i + 8 : i + 8 + 4], 16))
            peers.append(':'.join([ip_add, port]))

        return {
            'action' :action,
            'trans_id': trans_id,
            'interval': interval,
            'leechers': leechers,
            'seeders': seeders,
            'peers': peers
        }