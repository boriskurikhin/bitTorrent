#!/usr/bin/env python

from metaparser import MetaContent
from communicator import Communicator

mp = MetaContent()
com = Communicator()

mp.parseFile('test.torrent')
com.get_peers(mp)