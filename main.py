from metaparser import MetaContent
from communicator import Communicator
from exchange.protocol import PeerProtocol, PeerFactory
from twisted.internet.endpoints import TCP4ClientEndpoint, TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.internet.endpoints import connectProtocol

mp = MetaContent()
mp.parseFile('test.torrent')

com = Communicator(mp)
#peers = com.get_peers()

print(com.peer_id)
print(mp.info_hash)

peers = []

server = TCP4ServerEndpoint(reactor, 8000)
peerFactory = PeerFactory()
server.listen(peerFactory)


def gotProtocol(p):
    p.sendHandshake()

for peer in peers:
    host, port = peer.split(':')
    point = TCP4ClientEndpoint(reactor, host, int(port))
    deferred = connectProtocol(point, PeerProtocol(peerFactory))
    deferred.addCallback(gotProtocol)

reactor.run()