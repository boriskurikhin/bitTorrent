from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory
from utilities.h2i import hash2ints
import struct

'''
    This is how we will communicate with peers
    over TCP.

    Good tutorial: https://benediktkr.github.io/dev/2016/02/04/p2p-with-twisted.html
'''
class PeerProtocol(Protocol):    
    def __init__(self, factory, state="SEND_HANDSHAKE"):
        self.factory = factory
        self.my_id = self.factory.peer_id # my peer id
        self.remote_peer_id = None # peer's id
    
    def connectionMade(self):
        print('NEW CONNECTION (PEER):', self.transport.getPeer())
        print('NEW CONNECTION (HOST):', self.transport.getHost())
        #self.sendHandshake()
    
    def connectionLost(self, reason):
        # if self.remote_peer_id in self.factory.peers:
        #     self.factory.peers.pop(self.remote_peer_id)
        print('DISCONNECT:', self.remote_peer_id)

    # TODO: Handle incoming data from peers
    def dataReceived(self, data):
        print('DATA RECEIVED:', data)
    
    # This function is triggered upon a new connection, it sends out a handshake
    def sendHandshake(self):
        print('SENDING HANDSHAKE:')
        payload = struct.pack('>B19sQ20B20B', *[19, b'BitTorrent protocol', 0, *self.factory.info_hash, *self.factory.peer_id])
        self.transport.write(payload)

class PeerFactory(Factory):
    def __init__(self, info_ints, peer_ints):
        self.info_hash = hash2ints(info_ints)
        self.peer_id = hash2ints(peer_ints)
        pass

    def startFactory(self):
        self.peers = {}

    def buildProtocol(self, addr):
        return PeerProtocol(self)