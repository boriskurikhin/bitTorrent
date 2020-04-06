import random
import struct
import hashlib
import ipaddress
from hexdump import hexdump
from utilities.h2i import hash2ints

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
        self.transaction_id = random.randint(1, (2 << (31 - 1)) - 1)
        payload = struct.pack('>QII20B20BQQQIIIiH', *[
            params['conn_id'], # Q
            1, # I
            self.transaction_id, #I
            *params['info_hash'], #20B
            *params['peer_id'], #20B
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
        action, trans_id, interval, leechers, seeders = struct.unpack('>IIIII', payload[:20])

        assert action == 1, 'Action response did not match 1'
        assert trans_id == self.transaction_id, 'Transaction id didn\'t match'
        print('%d seeders, %d leechers' % (seeders, leechers))

        peers = []

        # Extract a list of peers
        for i in range(20, len(payload), 6):
            ip_add = str(ipaddress.IPv4Address(int.from_bytes(payload[i : i + 4], byteorder='big')))
            port = str(int.from_bytes(payload[i + 4 : i + 6], byteorder='big'))
            peers.append(':'.join([ip_add, port]))

        return {
            'action' :action,
            'trans_id': trans_id,
            'interval': interval,
            'leechers': leechers,
            'seeders': seeders,
            'peers': peers
        }