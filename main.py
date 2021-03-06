#!/usr/bin/env python3

from metaparser import MetaContent
from communicator import Communicator
from protocol import PeerProtocol, PeerFactory
from twisted.internet.endpoints import TCP4ClientEndpoint, TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.internet.endpoints import connectProtocol
import os

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
    print('Welcome to БTorrent, enter the name of your torrent file:')
    
    file_name = input().strip()

    if not file_name.endswith('.torrent'):
        file_name += '.torrent'

    mp = MetaContent()
    mp.parseFile(file_name)

    com = Communicator(mp, False)
    peers = com.get_peers()

    download_dir = os.path.join(os.getcwd(), 'downloads')
    #create download directory, if we don't already have one
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    start_server(peers, mp.piece_length, mp.last_piece_len, mp)

    reactor.run()