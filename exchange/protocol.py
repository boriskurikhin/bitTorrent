from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory
from utilities.h2i import hash2ints
from exchange.piece import Piece
from time import time
import bitstring
import struct
import math

'''
    This is how we will communicate with peers
    over TCP.
    Good docs: https://twistedmatrix.com/documents/12.2.0/core/howto/servers.html
    Good tutorial: https://benediktkr.github.io/dev/2016/02/04/p2p-with-twisted.html
    p2p blockchain: https://github.com/benediktkr/ncpoc/blob/d3a3b48715ee9af664a59b49f4a4881352dd8fc8/network.py#L25
'''

class PeerProtocol(Protocol):    
    def __init__(self, factory):
        self.factory = factory
        self.has_handshaked = False # important for new connections
        self.bitfield = '0' * self.factory.num_pieces

        # 4 States that we maintain with each peer
        self.is_choking = True
        self.is_interested = False
        self.am_choking = True
        self.am_interested = False

        self.keep_alive = True

        self.payload_left = 0
        self.received = b''

    # Prints all currently connected peers
    def printPeers(self):
        if len(self.factory.peers) == 0: 
            print('There are no peers connected')
            return
        print('There are %d peers connected' % len(self.factory.peers))
        for peer in self.factory.peers:
            print('Peer', self.factory.peers[peer])

    def connectionMade(self):
        peer = self.transport.getPeer()
        print('Peer Connected', peer)
        self.factory.numberProtocols += 1 # increase the number of protocols
        self.remote_ip = peer.host + ':' + str(peer.port)

    def connectionLost(self, reason):
        self.factory.numberProtocols -= 1
        self.printPeers()
        print('Disconnection')

    # TODO: Handle incoming data from peers
    def dataReceived(self, data):
        if not self.has_handshaked: self.checkIncomingHandshake(data)
        else: self.receive_new_message(data)

    # Message ID: 5
    def parseBitfield(self, hex_str):
        print('Parsing bitfield from', self.remote_ip)
        # set this peer's bitfield value
        bitfield = bitstring.BitArray('0x' + hex_str[10 : ])
        # check that bitfield is valid    
        binary = bitfield.bin
        valid = True
        # Loop through overflow pieces
        for i in range(self.factory.num_pieces, len(binary)):
            if binary[i] == '1': valid = False

        # Any overflowing pieces should be 0
        if not valid: 
            self.transport.loseConnection()

        # They don't have any pieces
        if binary.count('1') == 0:
            self.transport.loseConnection()

        self.bitfield = binary[ : len(binary)] + self.bitfield[len(binary) : ]
        
        print('Verified Bitfield (' + self.remote_ip + ')')
        # We need to send interested message
        self.sendInterested()
    
    # Message ID: 4
    def parseHave(self, hex_str):
        piece_index = int(hex_str[10:], 16)
        self.bitfield = self.bitfield[:piece_index] + '1' + self.bitfield[piece_index + 1:]
        self.sendInterested()

    # When we know we have the full message, we need to handle it
    def handle_full_message(self, payload):
        hex_string = payload.hex()
       
        message_length = int(hex_string[ : 8], 16)
        mid = int(hex_string[8 : 10], 16)

        print('Handling id:', mid, '(' + self.remote_ip + ')')

        # The only one we got back so far
        if mid == 0:
            print('Received choke (' + self.remote_ip + ')')
            self.is_choking = True
            self.sendInterested() # If we're getting choked, try to get unchoked
        if mid == 1: 
            print('Received unchoke (' + self.remote_ip + ')')
            self.is_choking = False
            self.generate_request()
        if mid == 3: 
            pass
        if mid == 4:
            self.parseHave(hex_string)
        if mid == 5:
            self.parseBitfield(hex_string)
    
    def generate_request(self):
        if self.is_choking: 
            return
        # Find next block
        for i in range(0, self.factory.num_pieces):
            # Piece not full
            if self.factory.pieces[i].get_state() != 2:
                # Get block needed
                next_block = self.factory.pieces[i].get_next_available_block()

                while (i, next_block) in self.factory.requested:
                    next_block = self.factory.pieces[i].get_next_available_block()
                
                if next_block == -1:
                    continue
                
                self.factory.requested.add((i, next_block))
                # Send request
                print('Requesting piece (%d, %d) from ' % (i, next_block), '(' + self.remote_ip + ')')
                self.transport.write(struct.pack('>iBiii', *[13, 6, i, next_block, 2 ** 14]))
                break
    # Parsing a message
    def receive_new_message(self, message):
        
        if len(message) == 0:
            return
        
        hex_string = message.hex() # entire message in hex

        print('From (' + self.remote_ip + ')')
        print('Payload left', self.payload_left )
        print('Message', message)

        # if we aren't currently waiting on continuation of previous message
        if self.payload_left == 0:           
            payload_size = int(hex_string[ : 8], 16) # (message type + payload) in bytes

            # fixed size message, no payload
            if payload_size == 1:
                self.handle_full_message(bytes.fromhex(hex_string[ : 10]))
                self.receive_new_message(bytes.fromhex(hex_string[10 : ]))
            elif payload_size == 0:
                # It's a keep alive
                # TODO: do something with this
                self.keep_alive = True
            else:
                # did we receive a full message, or more perhaps?
                payload_length = len(hex_string[8:]) # counts hex chars (message type + payload)
                no_overflow = (payload_length >= (payload_size * 2))

                if no_overflow:
                    self.handle_full_message(bytes.fromhex(hex_string[ : (payload_size * 2) + 8])) # send full message to responding
                    self.receive_new_message(bytes.fromhex(hex_string[(payload_size * 2) + 8 : ])) # send the rest for a re-parse
                else:
                    # The beginning chunk of a message
                    self.payload_left = (payload_size * 2) - payload_length
                    self.received += message
        else:
            # received new chunk continuing the previous message
            payload_length = len(hex_string)
            no_overflow = (payload_length >= self.payload_left)

            if no_overflow:
                self.received += bytes.fromhex(hex_string[ : self.payload_left])         
                self.handle_full_message(self.received) # parse current
                
                payload_end = self.payload_left
                self.payload_left = 0
                self.received = b''
                
                self.receive_new_message(bytes.fromhex(hex_string[payload_end : ])) # parse rest
            else:
                self.payload_left -= payload_length
                self.received += message

    # Check to see if the incoming handshake is valid
    def checkIncomingHandshake(self, payload):
        hex_string = payload.hex()
        payload_len = len(hex_string) # in case we have other things with the handshake
        print('Checking incoming handshake')

        # Extract a bunch of data from the payload
        pstrlen = int(hex_string[ : 2], 16)
        pstr = bytes.fromhex(hex_string[2 : 2 + 2 * 19]).decode('utf-8') #ends at 40
        reserved = int(hex_string[40  :40 + 2 * 8])
        info_hash = hex_string[56 : 56 + 40]
        self.client_id = hex_string[56 + 40 : 56 + 40 + 40]

        # Make sure we don't exchange handshakes with ourselves. 
        if self.client_id.upper() == self.factory.peer_id_hex.upper():
            self.transport.loseConnection()

        # The hash requested does not match
        if info_hash.upper() != self.factory.info_hash_hex.upper():
            self.transport.loseConnection()

        self.has_handshaked = True
        self.add_peer()

        # do we have more data? 
        payload_len -= 136

        if payload_len > 0:
        #    print ('Sent data along with handshake!', bytes.fromhex(hex_string[136:]))
            self.receive_new_message(bytes.fromhex(hex_string[136:]))

    def add_peer(self):
        self.factory.peers[self.client_id] = (self.remote_ip, time())
        self.printPeers()

    # This function is triggered upon a new connection, it sends out a handshake
    def sendHandshake(self):
        payload = struct.pack('>B19sQ20B20B', *[19, b'BitTorrent protocol', 0 , *self.factory.info_hash, *self.factory.peer_id])
        self.transport.write(payload)
    
    # We are interested
    def sendInterested(self):
        if not self.is_interested or self.is_choking:
            self.is_interested = True
            payload = struct.pack('>iB', *[1, 2])
            self.transport.write(payload)

class PeerFactory(Factory):
    def __init__(self, info_h, peer_h, num_pieces, piece_length, last_piece_length, piece_hashes):
        self.info_hash = hash2ints(info_h)
        self.peer_id = hash2ints(peer_h)

        self.info_hash_hex = info_h
        self.peer_id_hex = peer_h

        self.num_pieces = num_pieces # num total pieces
        self.piece_length = piece_length # length of one piece in bytes
        self.last_piece_length = last_piece_length
        self.piece_hashes = piece_hashes # hashes of all pieces

        self._block_length = 2 ** 16
        self._blocks_per_piece = self.piece_length // self._block_length
        self._blocks_per_last_piece = self.last_piece_length // self._block_length
        
        if self.piece_length - (self._block_length * self._blocks_per_piece) != 0:
            self._blocks_per_piece += 1
        if self.last_piece_length - (self._block_length * self._blocks_per_last_piece) != 0:
            self._blocks_per_last_piece += 1

        self.pieces = []

        for i in range(0, self.num_pieces - 1):
            self.pieces.append(Piece(self._blocks_per_piece, self.piece_length, i))
        
        self.pieces.append(Piece(self._blocks_per_last_piece, self.last_piece_length, self.num_pieces - 1))

        self.numberProtocols = 0
        
        # TODO: this is very inefficient
        self.requested = set()
    
    def startFactory(self):
        self.peers = {}
       

    def buildProtocol(self, addr):
        return PeerProtocol(self)