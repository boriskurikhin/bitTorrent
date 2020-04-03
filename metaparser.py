#!/usr/bin/env python

from bcoding import bencode, bdecode
from datetime import datetime
import hashlib
'''
    This class is responsible for opening a .torrent file
    and extract all the necessary information about the
    upcoming download. We are going to be needing an instance
    of this object a lot.
'''
class MetaContent: 
    def __init__(self):
        self.multi_file = False

    # Just dumps all the file information (nicely formatted)
    def file_info(self):
        print('\nFile Info:\n---------------')
        print('%s:\t\t%s' % ('name', self.name))
        print('%s:\t%s\n' % ('created', datetime.utcfromtimestamp(self.creation_date).strftime('%Y-%m-%d %H:%M:%S')))
        print('%s:\t%s' % ('# pieces', len(self.pieces)))
        print('%s:\t%s bytes' % ('piece len', self.piece_length))
        print('%s:\t%s bytes' % ('last piece', self.last_piece_len))
        print('%s:\t\t%s bytes' % ('total', self.length))
        print('%s:\t%s' % ('info-hash', self.info_hash.upper()))
    
    def parseFile(self, path_to_file):
        self.path_to_file = path_to_file
        self._open_file(path_to_file)

    '''
        This private function opens up the .torrent file, 
        and decodes its' contents into a MetaContent instance
    '''
    def _open_file(self, path_to_file):
        #read torrent file as binary object
        with open(self.path_to_file, 'rb') as meta_file:
            self.decoded = bdecode(meta_file.read())

        #check to see if it's a multi-file torrent
        if 'files' in self.decoded['info']:
            self.multi_file = True

        '''
            This stuff doesn't care whether or not it's a
            multi-file torrent
        '''
        # extract the creation date 
        self.creation_date = self.decoded['creation date']
        # extract the announce url
        self.announce = self.decoded['announce']
        # calculates info hash
        self.info_hash = hashlib.sha1(
            bencode(self.decoded['info'])
        ).hexdigest()

         # extract piece length
        self.piece_length = self.decoded['info']['piece length']
        # extract pieces
        self.pieces_hex = self.decoded['info']['pieces'].hex()
        #piece hashes will go here
        self.pieces = []
        
        # 1 hex - 4 bits
        # 2 hex - 1 byte
        # 40 hex = 20 bytes

        # extract all the piece sha-1 hashes (don't know if I need this yet)
        for i in range(0, len(self.pieces_hex), 40):
            hex_string = self.pieces_hex[i : i + 40]
            self.pieces.append(hex_string)
        
        # extract name
        self.name = self.decoded['info']['name']

        if not self.multi_file:
            # extract length
            self.length = self.decoded['info']['length']
            self.last_piece_len = self.length - self.piece_length * (len(self.pieces) - 1)
        else:
            #TODO: add implementation for multiple files
            self.files = self.decoded['info']['files']
       
        self.file_info()