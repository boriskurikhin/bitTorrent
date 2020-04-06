from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory
from utilities.h2i import hash2ints
from tqdm import tqdm
from time import time
from enum import Enum
import hashlib
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
        self.bitfield = bitstring.BitArray(self.factory.num_pieces)
        self.have_handshaked = False
        # 4 States that we maintain with each peer
        # self.is_choking = True
        # self.is_interested = False
        self.am_choking = True
        self.am_interested = False
        self.waiting_from_me = bitstring.BitArray(self.factory.num_pieces)

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
            print('Peer', peer)

    def connectionMade(self):
        peer = self.transport.getPeer()
        # print('Peer Connected', peer)
        self.factory.numberProtocols += 1 # increase the number of protocols
        self.remote_ip = peer.host + ':' + str(peer.port)

    def connectionLost(self, reason):
        # if self.transport.getPeer() in self.factory.peers:
        #     self.factory.peers.pop(self.transport.getPeer())
        self.factory.numberProtocols -= 1

    def dataReceived(self, data):
        if not self.have_handshaked: self.checkIncomingHandshake(data)
        else: self.receiveNewMessage(data)

    # Message ID: 5
    def parseBitfield(self, hex_str):
        # set this peer's (could be partial) bitfield value
        update_bitfield = bitstring.BitArray('0x' + hex_str[10 : ])

        # They don't have any pieces
        if 1 not in update_bitfield:
            self.transport.loseConnection()

        self.bitfield = update_bitfield[:update_bitfield.len] + self.bitfield[update_bitfield.len:]
        
        # print('Verified Bitfield (' + self.remote_ip + ')')
        # We need to send interested message
        self.sendInterested()
    
    # Message ID: 4
    def parseHave(self, hex_str):
        piece_index = int(hex_str[10:10+8], 16)
        self.bitfield[piece_index] = 1
        # if we don't have this piece, and we haven't asked anyone
        self.sendInterested()

    # When we know we have the full message, we need to handle it
    def handleFullMessage(self, payload):
        hex_string = payload.hex()
       
        message_length = int(hex_string[ : 8], 16)
        mid = int(hex_string[8 : 10], 16)

        # print('Handling id:', mid, '(' + self.remote_ip + ')')

        # The only one we got back so far
        if mid == 0:
            # print('Received choke (' + self.remote_ip + ')')
            self.sendInterested() # If we're getting choked, try to get unchoked
            self.am_choking = True
        elif mid == 1: 
            # print('Received unchoke (' + self.remote_ip + ')')
            self.am_choking = False
            self.generateRequest()
        elif mid == 3: 
            pass
        elif mid == 4:
            self.parseHave(hex_string)
        elif mid == 5:
            self.parseBitfield(hex_string)
        elif mid == 6:
            pass
        elif mid == 7:
            self.parse_block(hex_string, message_length)
        elif mid == 8:
            pass
        elif mid == 9:
            pass
        else:
            self.checkIncomingHandshake(payload)

    def get_block(self, pi, bi):
        return self.factory.bitfield[pi * self.factory.blocks_in_whole_piece + bi]

    def have_piece(self, pi):
        for i in range(pi * self.factory.blocks_in_whole_piece, pi * self.factory.blocks_in_whole_piece + self.factory.blocks_in_whole_piece):
            if not self.factory.bitfield[i]:
                return False
        return True

    # only use if hashes don't match
    def validate_piece(self, pi):
        # check if hash matches
        if not self.__checkHash(pi):
            # if not, unset all blocks we thought we had right
            for i in range(pi * self.factory.blocks_in_whole_piece, pi * self.factory.blocks_in_whole_piece + self.factory.blocks_in_whole_piece):
                self.factory.bitfield[i] = 0
            return False
        return True

    
    def set_block(self, pi, bi, val):
        self.factory.bitfield[pi * self.factory.blocks_in_whole_piece + bi] = val
    

    def parse_block(self, hex_string, message_length):
        length_of_block = message_length - 9 # 9 bytes are reserved for response info

        if length_of_block % self.factory.BLOCK_LEN != 0:
            return
        
        piece_index = int(hex_string[10:18], 16)
        byte_offset = int(hex_string[18:18+8], 16)
        block_index = byte_offset // self.factory.BLOCK_LEN

        if self.get_block(piece_index, block_index) or self.have_piece(piece_index):
            return

        self.factory.data[piece_index][block_index] = bytes.fromhex(hex_string[18 + 8:])
        self.set_block(piece_index, block_index, 1)

        if piece_index != self.factory.num_pieces - 1:
            if self.have_piece(piece_index) and self.validate_piece(piece_index):
                self.factory.pieces_need -= 1
                self.writePieceToFile(piece_index)
                self.generateRequest()
        else:
            if self.have_piece(piece_index) and self.validate_piece(piece_index):
                self.factory.pieces_need -= 1
                self.writePieceToFile(piece_index)
                self.generateRequest()

        
        # Someone wrote the last piece
        if self.factory.pieces_need <= 1:
            print('File download complete...')
            self.factory.file.close()

    def __checkHash(self, pi):
        temp = b''
        for block in self.factory.data[pi]: temp += block
        piece_hash = hashlib.sha1(temp).hexdigest().upper()
        expected_hash = self.factory.piece_hashes[pi].upper()
        return piece_hash == expected_hash

    def writePieceToFile(self, pi):
        self.factory.file.seek(pi * self.factory.piece_length)
        self.factory.progress.update(1)
        # print('Download: %d%% complete' %  )
        for bi in range(len(self.factory.data[pi])):
            self.factory.file.write(self.factory.data[pi][bi])
    
    def generateRequest(self):
        # we don't need anything anymore
        if self.factory.pieces_need <= 1:
            return
        # go through each piece
        for pi in range(self.factory.num_pieces):
            if self.have_piece(pi): continue 
            if pi != self.factory.num_pieces - 1:
                for bi in range(self.factory.blocks_in_whole_piece):
                    if not self.get_block(pi, bi):
                        req = struct.pack('>iBiii', *[13, 6, pi, bi * self.factory.BLOCK_LEN, self.factory.BLOCK_LEN])
                        self.transport.write(req)
            else:
                offset = 0
                for bi in range(self.factory.blocks_in_last_piece):
                    if not self.get_block(pi, bi):
                        if self.factory.last_piece_length - offset <= self.factory.BLOCK_LEN: req_size = self.factory.last_piece_length - offset
                        else: req_size = self.factory.BLOCK_LEN
                        req = struct.pack('>iBiii', *[13, 6, pi, bi * self.factory.BLOCK_LEN, req_size])
                        self.transport.write(req)
                    offset += self.factory.BLOCK_LEN
    
    # Parsing a message
    def receiveNewMessage(self, message):
        if len(message) == 0:
            return
        
        hex_string = message.hex() # entire message in hex

        # print('From (' + self.remote_ip + ')')
        # print('Payload left', self.payload_left )
        # print('Message', message)

        # if we aren't currently waiting on continuation of previous message
        if self.payload_left == 0:           
            payload_size = int(hex_string[ : 8], 16) # (message type + payload) in bytes

            # fixed size message, no payload
            if payload_size == 1:
                self.handleFullMessage(bytes.fromhex(hex_string[ : 10]))
                self.receiveNewMessage(bytes.fromhex(hex_string[10 : ]))
            elif payload_size == 0:
                # It's a keep alive
                # TODO: do something with this
                self.keep_alive = True
            else:
                # did we receive a full message, or more perhaps?
                payload_length = len(hex_string[8:]) # counts hex chars (message type + payload)
                no_overflow = (payload_length >= (payload_size * 2))

                if no_overflow:
                    self.handleFullMessage(bytes.fromhex(hex_string[ : (payload_size * 2) + 8])) # send full message to responding
                    self.receiveNewMessage(bytes.fromhex(hex_string[(payload_size * 2) + 8 : ])) # send the rest for a re-parse
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
                self.handleFullMessage(self.received) # parse current
                
                payload_end = self.payload_left
                self.payload_left = 0
                self.received = b''
                
                self.receiveNewMessage(bytes.fromhex(hex_string[payload_end : ])) # parse rest
            else:
                self.payload_left -= payload_length
                self.received += message

    # Check to see if the incoming handshake is valid
    def checkIncomingHandshake(self, payload):
        hex_string = payload.hex()
        payload_len = len(hex_string) # in case we have other things with the handshake
        # print('Checking incoming handshake')

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

        self.add_peer()
        self.sendInterested()

        # do we have more data? 
        payload_len -= 136

        if payload_len > 0:
            self.receiveNewMessage(bytes.fromhex(hex_string[136:]))
        
    def add_peer(self):
        self.have_handshaked = True
        self.factory.peers.append(self.transport.getPeer())
        # self.factory.peers[self.client_id] = (self.remote_ip, time())
        # self.printPeers()

    # This function is triggered upon a new connection, it sends out a handshake
    def sendHandshake(self):
        payload = struct.pack('>B19sQ20B20B', *[19, b'BitTorrent protocol', 0 , *self.factory.info_hash, *self.factory.peer_id])
        self.transport.write(payload)
    
    # We are interested
    def sendInterested(self):
        payload = struct.pack('>iB', *[1, 2])
        self.transport.write(payload)
        # print('Interested')

class PeerFactory(Factory):
    def __init__(self, info_h, peer_h, num_pieces, piece_length, last_piece_length, file_name, piece_hashes):
        self.info_hash = hash2ints(info_h)
        self.peer_id = hash2ints(peer_h)

        self.info_hash_hex = info_h
        self.peer_id_hex = peer_h

        self.num_pieces = num_pieces # num total pieces
        
        self.piece_length = piece_length # length of one piece in bytes
        self.last_piece_length = last_piece_length # length of last piece in bytes

        self.BLOCK_LEN = 2 ** 14
        self.file_name = file_name
        self.file = open('downloads/' + self.file_name, 'wb')
        self.piece_hashes = piece_hashes
        self.pieces_need = self.num_pieces

        self.progress = tqdm(total=self.num_pieces, initial=1)

        # TODO: add logic for this
        assert self.piece_length % self.BLOCK_LEN == 0, 'piece len not divisible by block size'

        self.blocks_in_whole_piece = self.piece_length // self.BLOCK_LEN
        self.blocks_in_last_piece = int(math.ceil(self.last_piece_length / self.BLOCK_LEN))

        # print(self.num_pieces, self.piece_length, self.BLOCK_LEN, self.blocks_in_whole_piece, self.blocks_in_last_piece)
        # raise Exception('Debug')

        # Figure out a better way to store block data maybe?
        self.data = []
        for i in range(self.num_pieces - 1):
            blocks = []
            for j in range(self.blocks_in_whole_piece):
                blocks.append(b'')
            self.data.append(blocks)
        blocks = []
        for i in range(self.blocks_in_last_piece):
            blocks.append(b'')
        self.data.append(blocks)
        
        self.peers = []
        self.bitfield = bitstring.BitArray((self.num_pieces - 1) * self.blocks_in_whole_piece + self.blocks_in_last_piece)
        
        self.numberProtocols = 0
       
    def buildProtocol(self, addr):
        return PeerProtocol(self)