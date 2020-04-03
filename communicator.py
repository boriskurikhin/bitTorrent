from metaparser import MetaContent

class Communicator:
    def get_peers(self, meta_file):
        
        # make sure the argument is correct
        if type(meta_file) != MetaContent:
            raise Exception('meta_file must be of type MetaContent')
        