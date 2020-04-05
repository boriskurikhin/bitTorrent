import hashlib

class Piece:
    '''
        Describes one of piece of the file
        Each piece has a certain amount of blocks
        Each block has a state, and 2 ** 14 bytes of data
    '''
    def __init__(self, blocks_per_piece, piece_size, piece_index, last_piece = False):
        self.blocks_per_piece = blocks_per_piece
        self.piece_size = piece_size
        self.piece_index = piece_index
        self.blocks_filled = 0
    #    self.block_index = 0

        self.blocks = [b'' ] * self.blocks_per_piece # DATA
        self.piece_state = 0 # EMPTY

    # def get_block_index():
    #     return self.block_index

    def get_state(self):
        return self.piece_state

    def get_next_available_block(self):
        for i in range(0, self.blocks_per_piece):
            if len(self.blocks[i]) == 0:
                return i
        return -1

    def get_piece_hash(self):
        assert self.piece_state == 2, 'Attempting to hash an unfinished piece'
        return hashlib.sha1(b''.join(self.blocks)).hexdigest()

    def get_piece(self):
        assert self.piece_size == len(b''.join(self.blocks)), 'Invalid piece size'
        assert self.piece_state == 2, 'Attempting to read an unfinished piece'
        return b''.join(self.blocks)

    def write_block(self, data, index):
        assert self.piece_state != 2, 'Attempting a write on an already full piece'
        assert len(self.blocks[index]) == 0, 'Attempting to overwrite a block'

        self.blocks[index] = data #write data to block
        
        self.blocks_filled += 1

        # we now have at least one block
        if self.piece_state == 0: 
            self.piece_state = 1
        
        # this piece is full
        if self.blocks_filled == self.blocks_per_piece:
            self.piece_state = 2

    

    
