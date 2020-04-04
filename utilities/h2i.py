
# Really simple utility function that converts string hex
# hash into a byte array, so that we can pack it. 
def hash2ints(hash):
    assert len(hash) == 40, 'Not a valid hex hash'
    
    result = []
    for i in range(0, 40, 2):
        result.append(int(hash[i : i + 2], 16))
    
    return result