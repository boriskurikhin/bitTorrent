from metaparser import MetaContent
from communicator import Communicator
from exchange.protocol import PeerProtocol, PeerFactory
from twisted.internet.endpoints import TCP4ClientEndpoint, TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.internet.endpoints import connectProtocol

def gotProtocol(p):
    p.sendHandshake()

def start_server(peers, num_pieces, piece_length):
    print(peers)
    
    server = TCP4ServerEndpoint(reactor, 8000)
    peerFactory = PeerFactory(mp.info_hash, com.peer_id, num_pieces, piece_length)
    server.listen(peerFactory)

    for peer in peers:
        host, port = peer.split(':')
        # reactor.connectTCP(host, int(port), PeerProtocol(peerFactory) )
        point = TCP4ClientEndpoint(reactor, host, int(port))
        deferred = connectProtocol(point, PeerProtocol(peerFactory))
        deferred.addCallback(gotProtocol)
    

# Main method
if __name__ == '__main__':
    mp = MetaContent()
    mp.parseFile('test.torrent')

    com = Communicator(mp)
    peers = com.get_peers()

    start_server(peers, len(mp.pieces), mp.piece_length)

    reactor.run()
