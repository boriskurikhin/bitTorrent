from metaparser import MetaContent
from communicator import Communicator
from protocol import PeerProtocol, PeerFactory
from twisted.internet.endpoints import TCP4ClientEndpoint, TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.internet.endpoints import connectProtocol

def gotProtocol(p):
    p.sendHandshake(True)

def handleError(e):
    pass

def start_server(peers, piece_length, last_piece_length, mp):
    server = TCP4ServerEndpoint(reactor, 8000)
    peerFactory = PeerFactory(com.peer_id, piece_length, last_piece_length, mp, peers)
    server.listen(peerFactory)

    for peer in peers:
        host, port = peer.split(':')
        # reactor.connectTCP(host, int(port), PeerProtocol(peerFactory) )
        point = TCP4ClientEndpoint(reactor, host, int(port))
        deferred = connectProtocol(point, PeerProtocol(peerFactory))
        deferred.addCallback(gotProtocol)
        deferred.addErrback(handleError)
    
# Main method
if __name__ == '__main__':
    mp = MetaContent()
    mp.parseFile('test.torrent')

    com = Communicator(mp, False)
    peers = com.get_peers()

    start_server(peers, mp.piece_length, mp.last_piece_len, mp)

    reactor.run()
