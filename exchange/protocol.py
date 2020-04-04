from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory

'''
    This is how we will communicate with peers
    over TCP.

    Good tutorial: https://benediktkr.github.io/dev/2016/02/04/p2p-with-twisted.html
'''
class PeerProtocol(Protocol):    
    def __init__(self, factory, state="SEND_HANDSHAKE"):
        self.factory = factory
        self.my_id = self.factory.peer_id # my peer id
        self.peer_id = None # peer's id
        self.pstr = 'BitTorrent protocol'
        self.pstrlen = len(self.pstr)
    
    def connectionMade(self):
        print('Connection from', self.transport.getPeer())
        def connectionLost(self, reason):
            if self.peer_id in self.factory.peers:
                self.factory.peers.pop(self.peer_id)
            print(self.peer_id, 'disconnected')

    def dataReceived(self, data):
        print(data)
    
    def sendHandshake(self):
        self.transport.write(
            str(self.pstrlen) + \
            self.pstr + '00000000' + \
            'ef6ca3afb05ff8bc81ca8b8b4cc59cba120f34d1' + \
            '2d4273303030312d566a786f6e434e784d747352'
        )

class PeerFactory(Factory):
    def __init__(self):
        pass

    def startFactory(self):
        self.peers = {}
        self.peer_id = 'PEER ID'

    def buildProtocol(self, addr):
        return PeerProtocol(self)