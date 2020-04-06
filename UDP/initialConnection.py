import random
import struct
from hexdump import hexdump

class udpConnectionHelper:
    '''
        This is used with a UDP Tracker, upon
        very first connection. This is kind of
        like a handshake.

        64 + 32 + 32 bits = 128 bits = 16 bytes
    '''
   
    # The thing that I kept messing up was the endian order
    # https://docs.python.org/2/library/struct.html

    def pack_payload(self):
        self.transaction_id = random.randint(1, (2 << (31 - 1)) - 1)
        return struct.pack('>QII', 0x41727101980, 0, self.transaction_id)
    
    # We get 16 bytes back, 4 bytes = action, 4 bytes = trans_id, 8 bytes = connection_id
    # Returns connection id
    def unpack_payload(self, payload):
        action, trans_id, conn_id = struct.unpack('>IIQ', payload)
        # Make sure we received response correctly
        assert trans_id == self.transaction_id, 'Received invalid transaction id'
        assert action == 0, 'Received action that was not 0, must have error\'d out'
        return {
            'action': action,
            'trans_id': trans_id,
            'conn_id': conn_id
        }
