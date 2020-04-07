from bcoding import bencode, bdecode
from datetime import datetime
import hashlib
import urllib.parse

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
        print('%s:\t\t"%s"' % ('name', self.name))
        print('%s:\t%s\n' % ('created', datetime.utcfromtimestamp(self.creation_date).strftime('%Y-%m-%d %H:%M:%S')))
        print('%s:\t%s' % ('# pieces', self.num_pieces))
        print('%s:\t%s bytes' % ('piece len', self.piece_length))
        print('%s:\t%s bytes' % ('last piece', self.last_piece_len))
        print('%s:\t\t%s bytes' % ('total', self.length))
        if self.multi_file:
            print('-----(# %d files)------' % (len(self.files)))
            for f in self.files:
                print('%s:\t(%d bytes)' % (f['path'], f['length']))
            print('------end------')
        print('%s:\t%s' % ('info-hash', self.info_hash.hex()))
    
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
        self.announce = urllib.parse.urlparse(self.decoded['announce'])
        print(self.decoded['announce'])
        # calculates info hash
        self.info_hash = hashlib.sha1(
            bencode(self.decoded['info'])
        ).digest()

         # extract piece length
        self.piece_length = self.decoded['info']['piece length']
        
        # extract pieces (in bytes)
        self.pieces = self.decoded['info']['pieces']
        self.num_pieces = len(self.pieces) // 20
        
        # extract name / dictionary as to where to store the files
        self.name = self.decoded['info']['name']

        if not self.multi_file:
            # extract length
            self.length = self.decoded['info']['length']
            self.last_piece_len = self.length - self.piece_length * (self.num_pieces - 1)
        else:
            self.files = []
            self.length = 0
            for f in self.decoded['info']['files']:
                self.length += int(f['length'])
                self.files.append({ 'length': int(f['length']), 'path': f['path'][0] })
            self.last_piece_len = self.length - self.piece_length * (self.num_pieces - 1)
        self.file_info()