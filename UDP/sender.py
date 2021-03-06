import socket
import time
import random
class Sender:
    '''
        Helper class, ultimately used to send packets and receive
        packets back, as well as, validating to make sure all the 
        data has been sent/received correctly
    '''
    def __init__(self):
        self.limit = 5
    
    def send_packet(self, main_socket, address, data):
        # we will be parsing this value later on
        main_socket.sendto(data, address)
        timedOut = False
        received = b''
        # our main request loop, just keeps trying to read data from the server
        while True:
            try:
                # read 4096 bytes into a buffer
                buffer = main_socket.recv(4096)
                received += buffer
                # if we received data, we don't care anymore
                if len(received) > 0:
                    break 
            except socket.timeout as e:
                timedOut = True
                self.limit -= 1
                break
        if timedOut:
            if self.limit >= 0:
                time.sleep(random.uniform(0.3, 2)) # sleep a random amount of time
                received = self.send_packet(main_socket, address, data) # try again, recursively
            else: return received
        # assert len(received) > 0, 'Did not receive anything from the server'
        return received


        



            

