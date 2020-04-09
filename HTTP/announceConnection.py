import ipaddress
import requests
import bcoding

class httpAnnounceHelper:
    def pack_request(self, params):
        p = {
            'info_hash': params['info_hash'],
            'peer_id': params['peer_id'],
            'port': 8000,
            'uploaded': 0,
            'downloaded': 0,
            'left': str(params['left']),
            'compact': '1',
            'event': 'started',
        }
        url = params['announce'].scheme + '://' + params['announce'].netloc + params['announce'].path
        resp = requests.get(url, params=p)
        return resp.content
    
    def unpack_request(self, req):
        #i think we might have to change the endianness of the response
        decoded = bcoding.bdecode(req)
        print('%d seeders, %d leechers' % (decoded['complete'], decoded['incomplete']))
        peers = []
        for i in range(0, len(decoded['peers']), 6):
            ip_add = str(ipaddress.IPv4Address(int.from_bytes(decoded['peers'][i : i + 4], byteorder='big')))
            port = str(int.from_bytes(decoded['peers'][i + 4 : i + 6], byteorder='big'))
            peers.append(':'.join([ip_add, port]))
        return peers