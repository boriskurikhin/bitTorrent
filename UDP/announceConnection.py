import random
import struct

class udpAnnounceHelper:
    '''
        This is used with a UDP Tracker, upon
        the announce. This is kind of
        like a handshake.

        64 + 32 + 32 + 8[20] + 8[20] + 64 + 64 + 64 + 32 + u32 + u32 + 32 + u16 + u16
        =  8 + 4 + 4 + 20 + 20 + 8 + 8 + 8 + 4 + 4 + 4 + 4 + 2
        = 100 bytes (total packet size)
    '''
   
    # The thing that I kept messing up was the endian order
    # https://docs.python.org/2/library/struct.html

    '''
        Generates a pretty hefty announce payload
    '''
    def pack_payload(self, params):
        self.transaction_id = random.randint(1, 2 ** 31)

        conn_id = params['conn_id'].to_bytes(8, byteorder='big')
        trans_id = self.transaction_id.to_bytes(4, byteorder='big')
        action = 0x1.to_bytes(4, byteorder='big') # =1 means announce
        _info_hash = [] # temporary value to store individual bytes of the hash
        _peer_id = []

        # loops through the hash hex, and creates array of 2 byte integers
        for i in range(0, 40, 2):
            _info_hash.append(int(params['info_hash'][i : i + 2], 16))
            _peer_id.append(int(params['peer_id'][i : i + 2], 16))

        # unsigned bytes
        info_hash = struct.pack('>20B', *_info_hash)
        peer_id = struct.pack('>20B', *_peer_id)
        
        # download quantitative info
        downloaded = 0x0.to_bytes(8, byteorder='big')
        left = params['left'].to_bytes(8, byteorder='big')
        uploaded = 0x0.to_bytes(8, byteorder='big')
        event = 0x0.to_bytes(4, byteorder='big') # not sure about this one, could be 2
        ip = 0x0.to_bytes(4, byteorder='big')
        key = random.randint(1, 2 ** (32 - 1)).to_bytes(4, byteorder='big') # random key?
        num_want = 0xffffffff.to_bytes(4, byteorder='big') # default (-1)
        port = 0x1f40.to_bytes(2, byteorder='big') # 0x1f40 -> 8000
        # no extensions

        payload = conn_id + action + trans_id + info_hash + \
               peer_id + downloaded + left + uploaded + event + \
               ip + key + num_want + port

        print(payload)


        assert len(payload) == 98, 'Announce payload was not generaeted correctly'
        return payload
    
    # We get 16 bytes back, 4 bytes = action, 4 bytes = trans_id, 8 bytes = connection_id
    # Returns connection id
    def unpack_payload(self, payload):
        pass
        # hex_string = payload.hex() # grab the hex value of the payload
        
        # action = int(hex_string[ : 8], 16)
        # trans_id = int(hex_string[8 : 16], 16)
        # conn_id = int(hex_string[16 : ], 16)

        # Make sure we received response correctly
        # assert trans_id == self.transaction_id, 'Received invalid transaction id'
        # assert action == 0, 'Received action that was not 0, must have error\'d out'

        # return (action, trans_id, conn_id)
