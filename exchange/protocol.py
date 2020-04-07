from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory
from utilities.h2i import hash2ints
from hexdump import hexdump
from tqdm import tqdm
from time import time
from enum import Enum
import hashlib
import bitstring
import struct
import random
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
        self.handshakeSent = False
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
    def parseBitfield(self, payload):
        # set this peer's (could be partial) bitfield value
        update_bitfield = bitstring.BitArray('0x' + payload.hex())

        # They don't have any pieces
        if 1 not in update_bitfield:
            self.transport.loseConnection()

        self.bitfield = update_bitfield[:update_bitfield.len] + self.bitfield[update_bitfield.len:]
        
        # print('Verified Bitfield (' + self.remote_ip + ')')
        # We need to send interested message
        self.sendInterested()
    
    # Message ID: 4
    def parseHave(self, payload):
        piece_index, = struct.unpack('>I', payload[:4])
        self.bitfield[piece_index] = 1
        # if we don't have this piece, and we haven't asked anyone
        self.sendInterested()

    # When we know we have the full message, we need to handle it
    def handleFullMessage(self, payload):
        hex_string = payload.hex()

        message_length, message_id = struct.unpack('>IB', payload[:5])

        # The only one we got back so far
        if message_id == 0:
            self.sendInterested() # If we're getting choked, try to get unchoked
            self.am_choking = True
        elif message_id == 1: 
            self.am_choking = False
            self.generateRequest()
        elif message_id == 3:
            pass
        elif message_id == 4:
            self.parseHave(payload[5:])
        elif message_id == 5:
            self.parseBitfield(payload[5:])
        elif message_id == 6:
            pass
        elif message_id == 7:
            self.parseBlock(payload[5:], message_length)
        elif message_id == 8:
            pass
        elif message_id == 9:
            pass
        else:
            self.checkIncomingHandshake(payload)

    def getBlock(self, pi, bi):
        return self.factory.bitfield[pi * self.factory.blocks_in_whole_piece + bi]

    def havePiece(self, pi):
        is_last_piece = pi == self.factory.num_pieces - 1
        incr = self.factory.blocks_in_last_piece if is_last_piece else self.factory.blocks_in_whole_piece
        for i in range(pi * self.factory.blocks_in_whole_piece, pi * self.factory.blocks_in_whole_piece + incr):
            if not self.factory.bitfield[i]:
                return False
        return True

    # only use if hashes don't match
    def validatePiece(self, pi):
        # check if hash matches
        is_last_piece = pi == self.factory.num_pieces - 1
        incr = self.factory.blocks_in_last_piece if is_last_piece else self.factory.blocks_in_whole_piece
        if not self.__checkHash(pi):
            # if not, unset all blocks we thought we had right
            for i in range(pi * self.factory.blocks_in_whole_piece, pi * self.factory.blocks_in_whole_piece + incr):
                self.factory.bitfield(False, i)
            return False
        return True
    
    def setBlock(self, pi, bi, val):
        self.factory.bitfield[pi * self.factory.blocks_in_whole_piece + bi] = val

    def parseBlock(self, payload, message_length):
        length_of_block = message_length - 9 # 9 bytes are reserved for response info

        if length_of_block % self.factory.BLOCK_LEN != 0:
            return
        
        piece_index, byte_offset = struct.unpack('>II', payload[:8])
        block_index = byte_offset // self.factory.BLOCK_LEN

        if self.getBlock(piece_index, block_index) or self.havePiece(piece_index):
            return

        self.factory.data[piece_index][block_index] = payload[8:]
        self.setBlock(piece_index, block_index, 1)

        if piece_index != self.factory.num_pieces - 1:
            if self.havePiece(piece_index) and self.validatePiece(piece_index):
                self.factory.pieces_need -= 1
                self.writePieceToFile(piece_index)
                self.generateRequest()
        else:
            if self.havePiece(piece_index) and self.validatePiece(piece_index):
                self.factory.pieces_need -= 1
                self.writePieceToFile(piece_index)
                self.generateRequest()

        # Someone wrote the last piece
        if self.factory.pieces_need <= 0:
            print('File download complete...')
            if self.factory.multi_file:
                self.writeToFiles()
            else: self.factory.file.close()

    def __checkHash(self, pi):
        piece = b''
        for block in self.factory.data[pi]: piece += block
        piece_hash = hashlib.sha1(piece).digest()
        expected_hash = self.factory.piece_hashes[pi * 20 : pi  * 20 + 20]
        return piece_hash == expected_hash

    def writePieceToFile(self, pi):
        self.factory.progress.update(1)
        if not self.factory.multi_file:
            self.factory.file.seek(pi * self.factory.piece_length)
            # print('Download: %d%% complete' %  )
            for bi in range(len(self.factory.data[pi])):
                self.factory.file.write(self.factory.data[pi][bi])
            self.factory.data[pi] = None #frees up memory??
        else: pass # TODO: figure out how to write files on the fly..(we're gonna have to pre-calculate that)

    def writeToFiles(self):
        bytes_written = 0 
        d = 'downloads/'
        fi = 0
        file_size = self.factory.files_info[fi]['length']
        f = open(d + self.factory.files_info[fi]['path'], 'wb')

        for pi in range(self.factory.num_pieces):
            data = b''
            for bi in range(len(self.factory.data[pi])):
                data += self.factory.data[pi][bi]
            len_data = len(data)
            if bytes_written + len_data <= file_size:
                f.write(data)
                bytes_written += len_data
            else:
                bytes_to_end = file_size - bytes_written
                data_to_end = data[ : bytes_to_end] # finish
                rem_data = data[bytes_to_end: ] # start
                f.write(data_to_end)
                f.close()
                # Close current file, open a new one, and begin writing to it
                fi += 1
                f = open(d + self.factory.files_info[fi]['path'], 'wb')
                file_size = self.factory.files_info[fi]['length']
                f.write(rem_data)
                bytes_written = len(rem_data)
    
    # lazy bitfield to prevent from ISP filtering
    def sendBitfield(self):
        we_have = []
        for i in range(self.factory.num_pieces):
            if self.havePiece(i): we_have.append(i)
        sample = random.sample(we_have, k = random.randint(1, len(we_have)))
        bitfield = bitstring.BitArray(self.factory.num_pieces)
        for idx in sample: 
            bitfield.set(True, idx)
        payload_len = 1 + self.factory.num_pieces
        payload = struct.pack('>IB%ds', *[payload_len, 5, *bitfield.bytes])
        # TODO: all the ones we didn't send, we need to send as HAVE messages
        self.transport.write(payload)


    def generateRequest(self):
        # we don't need anything anymore
        if self.factory.pieces_need <= 0:
            return
        
        # random piece sampling instead of sequential
        pieces_list = [*range(self.factory.num_pieces)]
        random.shuffle(pieces_list)

        for pi in pieces_list:
            if self.havePiece(pi): continue 
            if pi != self.factory.num_pieces - 1:
                for bi in range(self.factory.blocks_in_whole_piece):
                    if not self.getBlock(pi, bi):
                        req = struct.pack('>iBiii', *[13, 6, pi, bi * self.factory.BLOCK_LEN, self.factory.BLOCK_LEN])
                        self.transport.write(req)
            else:
                offset = 0
                for bi in range(self.factory.blocks_in_last_piece):
                    if not self.getBlock(pi, bi):
                        if self.factory.last_piece_length - offset <= self.factory.BLOCK_LEN: req_size = self.factory.last_piece_length - offset
                        else: req_size = self.factory.BLOCK_LEN
                        req = struct.pack('>iBiii', *[13, 6, pi, bi * self.factory.BLOCK_LEN, req_size])
                        self.transport.write(req)
                    offset += self.factory.BLOCK_LEN
    
    # Parsing a message
    def receiveNewMessage(self, payload):
        if len(payload) == 0: return
    
        # if we aren't currently waiting on continuation of previous message
        if self.payload_left == 0:
            try: payload_size, = struct.unpack('>I', payload[:4])
            except Exception as e: 
                # hexdump(payload)
                return # faulty payload

            # fixed size message, no payload
            if payload_size == 1:
                self.handleFullMessage(payload[:5])
                self.receiveNewMessage(payload[5:])
            elif payload_size == 0:
                # It's a keep alive
                # TODO: do something with this
                self.keep_alive = True
            else:
                # did we receive a full message, or more perhaps?
                payload_length = len(payload[4:]) # counts hex chars (message type + payload)
                no_overflow = payload_length >= payload_size

                if no_overflow:
                    self.handleFullMessage(payload[:payload_size + 4]) # send full message to responding
                    self.receiveNewMessage(payload[payload_size + 4:]) # send the rest for a re-parse
                else:
                    # The beginning chunk of a message
                    self.payload_left = payload_size - payload_length
                    self.received += payload
        else:
            # received new chunk continuing the previous message
            payload_length = len(payload)
            no_overflow = (payload_length >= self.payload_left)

            if no_overflow:
                self.received += payload[:self.payload_left]
                self.handleFullMessage(self.received) # parse current
                
                payload_end = self.payload_left
                self.payload_left = 0
                self.received = b''
                
                self.receiveNewMessage(payload[payload_end:]) # parse rest
            else:
                self.payload_left -= payload_length
                self.received += payload

    # Check to see if the incoming handshake is valid
    def checkIncomingHandshake(self, payload):
#        hexdump(payload)
        protocol_len, = struct.unpack('>B', payload[:1])
        protocol, reserved, info_hash, self.client_id = struct.unpack('>%ds8s20s20s' % protocol_len, payload[1:68])

        if protocol != b'BitTorrent protocol': 
            return

        # Make sure we don't exchange handshakes with ourselves. 
        if self.client_id == self.factory.peer_id:
            self.transport.loseConnection()

        # The hash requested does not match
        if info_hash != self.factory.info_hash:
            self.transport.loseConnection()

        # If we receiving back a handshake, and we still need stuff - we're interested
        if self.handshakeSent:
            self.addPeer()
            if self.factory.pieces_need > 0:
                self.sendInterested()
        else:
            self.handshakeSent = True
            self.sendHandshake()
            # TODO: send the bitfield of what we have
            self.sendBitfield()
            return # They're not supposed to send anything else until we returned the handshake

        # do we have more data? 
        payload_len = len(payload) - 68

        if payload_len > 0: self.receiveNewMessage(payload[68:])
        
    def addPeer(self):
        self.have_handshaked = True
        self.factory.peers.append(self.transport.getPeer())
        # self.factory.peers[self.client_id] = (self.remote_ip, time())
        # self.printPeers()

    # This function is triggered upon a new connection, it sends out a handshake
    def sendHandshake(self, originalPeer=False):
        if originalPeer: self.handshakeSent = True
        payload = struct.pack('>B19sQ20B20B', *[19, b'BitTorrent protocol', 0 , *self.factory.info_hash, *self.factory.peer_id])
        self.transport.write(payload)
    
    # We are interested
    def sendInterested(self):
        payload = struct.pack('>iB', *[1, 2])
        self.transport.write(payload)
        # print('Interested')

class PeerFactory(Factory):
    def __init__(self, peer_id, piece_length, last_piece_length, metadata):
        self.info_hash = metadata.info_hash
        self.peer_id = peer_id

        self.num_pieces = metadata.num_pieces # num total pieces
        
        self.piece_length = piece_length # length of one piece in bytes
        self.last_piece_length = last_piece_length # length of last piece in bytes

        self.BLOCK_LEN = 2 ** 14
        
        self.multi_file = metadata.multi_file

        # if we're not in multifile mode, we can write to downloads directly
        if not self.multi_file:
            self.file_name = metadata.name
            self.file = open('downloads/' + self.file_name, 'wb')
        else:
            self.files_info = metadata.files
        
        self.piece_hashes = metadata.pieces
        self.pieces_need = self.num_pieces - 1

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