from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory
from utilities.h2i import hash2ints
from time import time
import bitstring
import struct

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
        self.bitfield = None

        # 4 States that we maintain with each peer
        self.is_choking = True
        self.is_interested = False
        self.am_choking = True
        self.am_interested = False

        self.bytes_left = 0

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
        if self.has_handshaked == False:
            self.checkIncomingHandshake(data)
        else: 
            self.parseMessage(data)

    # Message ID: 5
    def parseBitfield(self, hex):
        # set this peer's bitfield value
        self.bitfield = bitstring.BitArray(hex[ : 10])

        # check that bitfield is valid    
        binary = self.bitfield.bin
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
        
        # We need to send interested message
        self.sendInterested()
        
    # Parsing the actual message
    def parseMessage(self, payload):
        hex_string = payload.hex()
        
        mlen = int(hex_string[ : 8], 16)
        mid = int(hex_string[8 : 10], 16)

        print('Message Id:', mid)

        # The only one we got back so far 
        if mid == 5:
            self.parseBitfield(hex_string)   

    # Check to see if the incoming handshake is valid
    def checkIncomingHandshake(self, payload):
        hex_string = payload.hex()

        print('Checking incoming handshake')

        # Extract a bunch of data from the payload
        pstrlen = int(hex_string[ : 2], 16)
        pstr = bytes.fromhex(hex_string[2 : 2 + 2 * 19]).decode('utf-8') #ends at 40
        reserved = int(hex_string[40  :40 + 2 * 8])
        info_hash = hex_string[56 : 56 + 40]
        self.client_id = hex_string[56 + 40 : ]

        # Make sure we don't exchange handshakes with ourselves. 
        if self.client_id.upper() == self.factory.peer_id_hex.upper():
            self.transport.loseConnection()

        # The hash requested does not match
        if info_hash.upper() != self.factory.info_hash_hex.upper():
            self.transport.loseConnection()

        self.has_handshaked = True

    def add_peer(self):
        print('Added', self.client_id, 'to peer list')
        self.factory.peers[self.client_id] = (self.remote_ip, time())
        self.printPeers()

    # This function is triggered upon a new connection, it sends out a handshake
    def sendHandshake(self):
        print('Sending handshake')
        payload = struct.pack('>B19sQ20B20B', *[19, b'BitTorrent protocol', 0, *self.factory.info_hash, *self.factory.peer_id])
        self.transport.write(payload)
    
    # We are interested
    def sendInterested(self):
        payload = struct.pack('>iB', *[1, 2])
        self.transport.write(payload)

class PeerFactory(Factory):
    def __init__(self, info_h, peer_h, num_pieces, piece_length):
        
        self.info_hash = hash2ints(info_h)
        self.peer_id = hash2ints(peer_h)

        self.info_hash_hex = info_h
        self.peer_id_hex = peer_h

        self.num_pieces = num_pieces
        self.pice_length = piece_length

        self.numberProtocols = 0
        self.have = '0' * self.num_pieces # we don't have shit lol
    
    def startFactory(self):
        self.peers = {}

    def buildProtocol(self, addr):
        return PeerProtocol(self)