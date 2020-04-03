import socket
class Sender:
    '''
        Helper class, ultimately used to send packets and receive
        packets back, as well as, validating to make sure all the 
        data has been sent/received correctly
    '''
    def send_packet(self, main_socket, address, data):
        # we will be parsing this value later on
        main_socket.sendto(data, address)
        received = b''
        # our main request loop, just keeps trying to read data from the server
        while True:
            try:
                # read 4096 bytes into a buffer
                buffer = main_socket.recv(4096)
                received += buffer
                print(buffer)
                if len(received) > 0:
                    break 
            except socket.timeout as e:
                print (e)
            except Exception as e:
                print (e)
                break
        assert len(received) > 0, 'Did not receive anything from the server'
        return received


        



            

