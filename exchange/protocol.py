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
        self.bitfield = '0' * self.factory.num_pieces

        # 4 States that we maintain with each peer
        self.is_choking = True
        self.is_interested = False
        self.am_choking = True
        self.am_interested = False

        self.bytes_left = 0
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
        if self.has_handshaked == False:
            self.checkIncomingHandshake(data)
        else: 
            self.receive_new_message(data)

    # Message ID: 5
    def parseBitfield(self, hex_str):
        # set this peer's bitfield value
        bitfield = bitstring.BitArray('0x' + hex_str[10 : ])

        # check that bitfield is valid    
        binary = bitfield.bin
        
        #valid = True

        # Loop through overflow pieces
        # for i in range(self.factory.num_pieces, len(binary)):
        #     if binary[i] == '1': valid = False

        # Any overflowing pieces should be 0
        # if not valid: 
        #     self.transport.loseConnection()

        # They don't have any pieces
        if binary.count('1') == 0:
            self.transport.loseConnection()

        self.bitfield = binary[ : len(binary)] + self.bitfield[len(binary) : ]
        
        # We need to send interested message
        self.sendInterested()
        
    # Parsing the actual message
    def receive_new_message(self, payload):
        hex_string = payload.hex()
        print('From:', self.remote_ip)

        # if we aren't currently waiting on continuation of previous message
        if self.bytes_left == 0:
            self.received = b''
            mlen = int(hex_string[ : 8], 16)
            mid = int(hex_string[8 : 10], 16)

            # did we receive a full message, or more perhaps?
            bytes_received = (len(hex_string) - 10) // 2
            is_full = mlen <= bytes_received

            print('Message (%d bytes, id: %d)' % (mlen, mid))
            print('Received %d of %d bytes' % (bytes_received, mlen))

            if is_full:
                 # The only one we got back so far
                if mid == 4:
                    print('Recieved full a HAVE message')
                if mid == 5:
                    print('Received full a BITFIELD message')
                    self.parseBitfield(hex_string)
            else:
                # The beginning chunk of a message
                self.bytes_left = mlen - bytes_received
                self.received += payload
                # Need to keep waiting on the rest
                print('Awaiting resot of message')
        else:
            bytes_received = len(hex_string) / 2
            is_rest = (bytes_received >= self.bytes_left)

            if is_rest:
                for i in range(0, self.bytes_left * 2, 2):
                    self.received += bytes.fromhex(hex_string[i : i + 2])
                self.bytes_left = 0
                self.receive_new_message(self.received)
            else:
                print('Should really never be this weird')
                self.bytes_left -= bytes_received
                self.received += payload

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

        # do we have more data? 
        payload_len -= (56 + 40 + 40)

        if payload_len > 0:
            self.receive_new_message(bytes.fromhex(hex_string[56 + 40 + 40 : ]))

    def add_peer(self):
        print('Added', self.client_id, 'to peer list')
        self.factory.peers[self.client_id] = (self.remote_ip, time())
        self.printPeers()

    # This function is triggered upon a new connection, it sends out a handshake
    def sendHandshake(self):
        print('Sending handshake')
        payload = struct.pack('>B19sQ20B20B', *[19, b'BitTorrent protocol', 0 , *self.factory.info_hash, *self.factory.peer_id])
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