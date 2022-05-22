import time
import sys

sys.path.append(".")

SEPARATOR = '-'
STR_SEPARATOR = ','

class Signature:
    def __init__(self, pk, sk, data):
        self.pk = pk
        self.data = str(pk) + str(data) # no crypto for now

    def validate(self, data):
        # mocked for now; will raise exception if not
        if self.data != str(self.pk) + str(data):
            raise(Exception('signature validation failed:', str(self.pk) + str(data), self.data))
    
    def __str__(self):
     return self.data

class Request:
    def __init__(self, payload, pk):
        self.pk = pk
        self.payload = payload
    def __str__(self) -> str:
        return self.payload + STR_SEPARATOR + self.pk

class Id:
    def __init__(self, sk, pk):
        self.pk = pk
        self.sk = sk

    def sign(self, data):
        return Signature(self.pk, self.sk, data) 

class Config:
    def __init__(self, faulty_time, faulty_cnt, client_patience = 2):
        self.faulty_time = faulty_time
        self.faulty_cnt = faulty_cnt
        self.client_patience = client_patience

class ClientRequests:
    def __init__(self, config):
        self.config = config
        self.requests = {}

    def __key(self, request):
        return request.pk + SEPARATOR + request.payload  

    def add(self, request, primary_pk = None):
        if primary_pk is None:
            self.requests[self.__key(request)] = (None, None, request)
        else:
            self.requests[self.__key(request)] = (primary_pk, time.time(), request)

    def delete(self, request):
        self.requests.pop(self.__key(request))

    def has(self, request):
        return self.__key(request) in self.requests
    
    def timer_faulty(self, request, primary_pk):
        key = self.__key(request)

        if key not in self.requests or self.requests[key][0] is None or \
            primary_pk != self.requests[key][0]:
            return False

        start_time = self.requests[key][1]

        if start_time == 0:
            return False
        
        return True if time.time() - start_time > self.config.faulty_time else False

    def reset_timer(self, request):
        self.requests[self.__key(request)] = (None, None, request)

    def get_all(self):
        return self.requests


class ViewSequence:
    def __init__(self, view, sequence, request):
        self.view = view
        self.sequence = sequence
        self.request = request

    def key(self):
        return str(self.view) + SEPARATOR + str(self.sequence)

class ViewSequenceState:
    def __init__(self):
        self.state = {}

    def add(self, view_sequence):
        self.state[view_sequence.key()] = view_sequence


# pk here is the public key of the primary
class AcceptedPrePrepared:
    def __init__(self):
        self.requests = {}

    def __key(self, view, sequence, pk):
        return str(view) + SEPARATOR + str(sequence) + SEPARATOR + str(pk)

    def has(self, view, sequence, pk = None):
        if pk is None:
            for key in self.requests:
                if key.startswith(str(view) + SEPARATOR + str(sequence)):
                    return True

            return False
        else:
            return self.__key(view, sequence, pk) in self.requests

    def add(self, view, sequence, pk, val):
        key = self.__key(view, sequence, pk)
        if self.has(view, sequence, pk):
            return
        
        self.requests[key] = val

    def get(self, view, sequence, pk):
        key = self.__key(view, sequence, pk)
        return self.requests[key]

    def get_all(self):
        return self.requests

    def clear(self):
        self.requests = {}


# pk here is the public key of the message sender
class PreparedMessages:
    def __init__(self, config, commit = False):
        self.config = config
        self.messages = {}
        self.commit = commit
        self.sent = set()

    def __sent_key(self, view, sequence):
        return str(view) + SEPARATOR + str(sequence)        

    def __key(self, view, sequence, signature):
        return self.__sent_key(view, sequence) + SEPARATOR + str(signature)

    def has(self, view, sequence, signature):
        key = self.__key(view, sequence, signature)

        return key in self.messages

    def add(self, view, sequence, signature, request):
        key = self.__key(view, sequence, signature)        
        self.messages[key] = request

    def get(self, view, sequence, signature):
        key = self.__key(view, sequence, signature)
        return self.messages[key]

    def get_all(self):
        return self.messages

    def set_sent(self, view, sequence):
        self.sent.add(self.__sent_key(view, sequence))

    def has_sent(self, view, sequence):
        return self.__sent_key(view, sequence) in self.sent

    def clear(self):
        self.messages = {}
        self.sent.clear()

    async def count_sufficient(self, view, sequence):
        total = 0
        multiplier = 1 if self.commit else 2

        # room for optimization
        for key in self.messages:
            if key.startswith(str(view) + SEPARATOR + str(sequence) + SEPARATOR):
                total += 1
                if total > multiplier*self.config.faulty_cnt: 
                    return True
        return False

    @staticmethod
    async def contains(messages, sequence, request):
        for key in messages:
            (view, _sequence, signature) = key.split(SEPARATOR) 
            _request = messages[key]
            if _sequence == sequence and _request.payload == request.payload:
                return True
        return False          

    # using notations from book
    async def build_omicron(self, new_view, theta, pk, sign_func):
        omicron = {}
        s_max = 0

        # not performance optimized
        for key in self.messages:
            (view, sequence, signature) = key.split(SEPARATOR)
            request = self.messages[key]
            if  await PreparedMessages.contains(theta, sequence, request) and sequence not in omicron:
                omicron[sequence] = (request, await sign_func(sequence, request))
                s_max = max(s_max, int(sequence))

        for i in range(1, s_max):
            s = str(i)
            if s not in omicron:
                print('adding ', s, 'to omicron')
                request =  Request('None', pk)
                omicron[s] = (request, await sign_func(i, request))

        return omicron

class ViewChangeRequests:
    def __init__(self, config):
        self.config = config
        self.requests = {}

    def __key(self, view, signature):
        return str(view) + SEPARATOR + str(signature)

    def add(self, view, signature, prepared_certs):
        self.requests[self.__key(view, signature)] = prepared_certs       

    async def count_sufficient(self, view):
        total = 0

        # room for optimization
        for key in self.requests:
            if key.startswith(str(view) + SEPARATOR):
                total += 1
                if total > 2*self.config.faulty_cnt: 
                    return True
        return False

    async def build_theta(self, view):
        theta = {}

        # room for optimization
        for key in self.requests:
            if key.startswith(str(view) + SEPARATOR):
                theta.update(self.requests[key])

        return theta




    