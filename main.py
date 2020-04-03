#!/usr/bin/env python

from metaparser import MetaContent
from communicator import Communicator

mp = MetaContent()
mp.parseFile('test.torrent')

com = Communicator(mp)
com.get_peers()