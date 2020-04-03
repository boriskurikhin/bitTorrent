import socket
class Sender:
    '''
        Helper class, ultimately used to send packets and receive
        packets back, as well as, validating to make sure all the 
        data has been sent/received correctly
    '''
    def send_packet(self, main_socket, address, data, expectedResponse):
        error_times = 0
        # we will be parsing this value later on
        received = b''
        
        # our main request loop, just keeps trying to read data from the server
        while error_times < 32:
            # send data 
            main_socket.sendto(data, address)
            try:
                # read 4096 bytes into a buffer
                buffer = main_socket.recv(4096)
                received += buffer

                # Sometimes we don't know what we're gonna get
                if expectedResponse != None:
                    # Pretty basic stuff, we need to be careful
                    if len(received) == expectedResponse:
                        break
                    elif len(received) > expectedResponse:
                        raise Exception('Too much data received!')
                else:
                    if len(received) == 0:
                        break

                received += buffer
            except socket.error as e:
                print(e)
                error_times += 1
            except Exception as e:
                print (e)
                error_times += 1
        
        assert len(received) == expectedResponse, 'Incorrect length response received'
        return received


        



            

