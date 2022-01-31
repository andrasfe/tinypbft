import sys
from unittest import result
sys.path.append(".")
import util

SEPARATOR = '-'

class Client:
    def __init__(self, id, config, network_map):
        self.id = id
        self.network_map = network_map
        self.config = config
        self.responses = {}
        self.confirmed_results = {}
        signature = util.Signature(id.pk, id.sk, 'some data')
        network_map.register_client(self, signature)

    async def submit_request(self, request):
        signature = util.Signature(self.id.pk, self.id.sk, str(request.pk) + str(request.payload))
        self.network_map.broadcast('client_request', {
            'request': request,
            'signature': signature
        })


    def __key(self, request, pk):
        return str(request.payload) + SEPARATOR + str(pk)

    def __confirmed(self, request, response):
        counter = 0

        for key in self.responses:
            (r, pk) = key.split(SEPARATOR)
            if r == request.payload and self.responses[key] == str(response):
                counter += 1

                if counter > self.config.faulty_cnt:
                    return True
        return False

    async def send_response(self, request, response, signature):
        sign_body = str(request.pk) + str(request.payload) + str(response)
        signature.validate(sign_body)
        self.responses[self.__key(request, signature.pk)] = response
        key = str(request.payload)
        if self.__confirmed(request, response) and key not in self.confirmed_results:
            self.confirmed_results[key] = result
            print('execution result:', response)
       