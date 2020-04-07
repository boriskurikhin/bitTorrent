from metaparser import MetaContent
from communicator import Communicator
from exchange.protocol import PeerProtocol, PeerFactory
from twisted.internet.endpoints import TCP4ClientEndpoint, TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.internet.endpoints import connectProtocol

def gotProtocol(p):
    p.sendHandshake(True)

def start_server(peers, piece_length, last_piece_length, mp):
    # print(peers)
    
    server = TCP4ServerEndpoint(reactor, 8000)
    peerFactory = PeerFactory(com.peer_id, piece_length, last_piece_length, mp)
    server.listen(peerFactory)

    for peer in peers:
        host, port = peer.split(':')
        # reactor.connectTCP(host, int(port), PeerProtocol(peerFactory) )
        point = TCP4ClientEndpoint(reactor, host, int(port))
        try: 
            deferred = connectProtocol(point, PeerProtocol(peerFactory))
            deferred.addCallback(gotProtocol)
        except Exception as e: pass
    
# Main method
if __name__ == '__main__':
    mp = MetaContent()
    mp.parseFile('test.torrent')

    com = Communicator(mp, False)
    peers = com.get_peers()

    start_server(peers, mp.piece_length, mp.last_piece_len, mp)

    reactor.run()
