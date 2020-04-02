from bcoding import bencode, bdecode
import hashlib
import json
'''
    This class is responsible for opening a .torrent file
    and extract all the necessary information about the
    upcoming download.
'''
class MetaParser:
    
    def __init__(self, path_to_file):
        self.path_to_file = path_to_file
        self.open_file()

    '''
        We will open up the .torrent file, and decode
        its' contents
    '''
    def open_file(self):
        #read torrent file as binary object
        with open(self.path_to_file, 'rb') as meta_file:
            self.decoded = bdecode(meta_file.read())
    
        # calculate info hash
        info_hash = hashlib.sha1(
            bencode(
                self.decoded['info']
            )
        ).hexdigest()

        print(info_hash)


    
    