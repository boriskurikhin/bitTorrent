#!/usr/bin/env python

from bcoding import bencode, bdecode
import hashlib
import json
'''
    This class is responsible for opening a .torrent file
    and extract all the necessary information about the
    upcoming download.
'''
class MetaContent: 
    def __init__(self):
        self.multi_file = False
    
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
        self.pieces = []
        
        # 1 hex - 4 bits
        # 2 hex - 1 byte
        # 40 hex = 20 bytes

        for i in range(0, len(self.pieces_hex), 40):
            hex_string = self.pieces_hex[i : i + 40]
            self.pieces.append(hex_string)

        print(self.pieces)
        
        # extract name
        self.name = self.decoded['info']['name']


        
        
        
        # extract length
        self.length = self.decoded['info']['length']
        
       

        print(self.name, self.piece_length, self.length)

        #print(self.info_hash)


    
    