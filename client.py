import sys
from time import time, sleep
from unittest import result
sys.path.append(".")
import util

SEPARATOR = '-'

class Client:
    def __init__(self, id, config, network_map):
        self.id = id
        self.view = 0
        self.network_map = network_map
        self.config = config
        self.timers = {}
        self.responses = {}
        self.confirmed_results = {}
        signature = util.Signature(id.pk, id.sk, 'some data')
        network_map.register_client(self, signature)

    async def send_to_primary_request(self, request):
        signature = util.Signature(self.id.pk, self.id.sk, str(request.pk) + str(request.payload))
        primary = self.network_map.get_primary_for_view(self.view)
        key = str(request.payload)
        self.timers[key] = {'start': time()}
        self.network_map.send_to_node(primary, 'client_request', {
            'request': request,
            'signature': signature
        })

    async def broadcast_request(self, request):
        signature = util.Signature(self.id.pk, self.id.sk, str(request.pk) + str(request.payload))
        self.network_map.broadcast('client_request', {
            'request': request,
            'signature': signature
        })

    async def broadcast_request_if_timeout(self, request):
        key = str(request.payload)
        for i in range(self.config.client_patience):
            sleep(1)
            if key in self.confirmed_results.keys():
                return

        await self.broadcast_request(request)
        print('Client: Primary for view:', self.view, 'was faulty. Broadcasting now.')


    async def submit_request(self, request):
        await  self.send_to_primary_request(request)
        await self.broadcast_request_if_timeout(request)


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

    async def send_response(self, view, request, response, signature):
        sign_body = str(request.pk) + str(request.payload) + str(response)
        signature.validate(sign_body)
        self.responses[self.__key(request, signature.pk)] = response
        key = str(request.payload)
        if self.__confirmed(request, response) and key not in self.confirmed_results:
            self.view = view
            self.confirmed_results[key] = result
            self.timers[key]['end'] = time()

    def get_duration(self, key):
        return self.timers[key]['end'] - self.timers[key]['start']

    
       
    