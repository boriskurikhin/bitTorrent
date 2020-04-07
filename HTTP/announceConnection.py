import requests
import bcoding

class httpAnnounceHelper:
    def pack_request(self, params):
        info_hash = requests.utils.quote(params['info_hash'])
        peer_id = requests.utils.quote(params['peer_id'])
        # sketchy
        url = params['announce'].scheme + '://' + params['announce'].netloc + params['announce'].path
        url += '?info_hash=' + info_hash + '&peer_id=' + peer_id + '&port=8000&uploaded=0&downloaded=0&' + \
               'left=' + str(params['left']) + '&compact=1&event=started'
        resp = requests.get(url)
        return resp.text
    
    def unpack_request(self, req):
        enc = req.encode('utf-8')
        dec = bcoding.bdecode(enc.decode('utf-8'))
        print(enc)
        exit(0)