import time
import sys
sys.path.append(".")
from node import Node
import util
from enum import Enum
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
streamHandler = logging.StreamHandler(sys.stdout)
streamHandler.setLevel(logging.INFO)
logger.addHandler(streamHandler)
# print = logger.info

class NODE_TYPE(Enum):
    PRIMARY = 1
    BACKUP = 2
    REGULAR = 3

class NodeImpl(Node):
    def __init__(self, id, config, network_map, primary_node = None, type = NODE_TYPE.REGULAR):
        self.id = id
        self.config = config
        self.network_map = network_map
        self.client_requests = util.ClientRequests(config)
        self.primary_node = primary_node
        self._is_primary = (type == NODE_TYPE.PRIMARY)
        self.accepted_pre_prepared = util.AcceptedPrePrepared()
        self.prepared_messages = util.PreparedMessages(self.config)
        self.committed_messages = util.PreparedMessages(self.config, True)
        self.view_change_requests = util.ViewChangeRequests(self.config)
        self.view = 0
        self.sequence = 0
        self.faulty_view = -1

        signature = util.Signature(id.pk, id.sk, 'aaa')
        if type == NODE_TYPE.REGULAR:
            network_map.register_regular(self, signature)
        else:
            network_map.register_lead(self, signature)

    def get_pk(self):
        return self.id.pk
    
    def is_primary(self):
        return self._is_primary

    def __set_self_primary(self, new_view):
        print('I am the primary:', self.get_pk())
        self._is_primary = True
        self.view = new_view
        self.faulty_view = -1


    async def __sign(self, payload):
        return util.Signature(self.id.pk, self.id.sk, payload)


    def __sign_prepare_body(self, view, sequence, request):
        return str(view) + str(sequence) + str(request.payload) + str(request.pk) + str(request.payload)

    def __sign_new_view_body(self, new_view, theta, omicron):
        return str(new_view) + str(theta) + str(omicron)

    def __sign_view_change_body(self, new_view, theta):
        return (str(new_view) + str(theta))

    def __sign_client_request_body(self, request):
        return str(request.pk) + str(request.payload)

    def __sign_client_response_body(self, request, response):
        return str(request.pk) + str(request.payload) + str(response)


    async def __client_request_primary(self, request):
            self.sequence += 1
            await self.__primary_pre_prepare(request)

    async def  __client_request_backup(self, request):

        if self.client_requests.timer_faulty(request, self.primary_node.get_pk()):
            self.faulty_view = self.view
            print('view change request', self.get_pk(), self.view, request.payload)
            await self.__request_view_change()
            self.client_requests.reset_timer(request)
            return

        signature = await self.__sign(self.__sign_client_request_body(request))
        await self.primary_node.client_request(request, signature)
        self.network_map.send_to_primary_for_view(self.view, 'client_request', {
            'request': request,
            'signature': signature
        })

    async def client_request(self, request, signature):
        if not self.client_requests.has(request):
            signature.validate(self.__sign_client_request_body(request))
            self.client_requests.add(request, None if self.is_primary() else self.primary_node.get_pk())

        if self.is_primary():
            await self.__client_request_primary(request)
        else:
            await self.__client_request_backup(request)

    async def __prepared_message_valid(self, view, sequence, pk, request):
        # to be completed
        return True

    def __is_view_valid(self, view):
        if view == self.faulty_view or view != self.view:
            return False
        else:
            return True


    async def commit(self, view, sequence, request, signature):
        if not self.__is_view_valid(view):
            return

        sign_body = self.__sign_prepare_body(view, sequence, request)
        signature.validate(sign_body)

        if self.committed_messages.has_sent(view, sequence) or \
            self.committed_messages.has(view, sequence, signature):
            return

        if not await self.__prepared_message_valid(view, sequence, signature, request):
            return

        self.committed_messages.add(view, sequence, signature, request)

        if await self.committed_messages.count_sufficient(view, sequence):
            # has faulty timer expired?
            if request.payload != 'None':
                response = request.payload[::-1]
                sign_response_body = self.__sign_client_response_body(request, response)
                signature = await self.__sign(sign_response_body)
                node = self.network_map.get_node(request.pk)
                self.network_map.send_to_node(node, 'send_response', {
                    'view': view,
                    'request': request,
                    'response': response,
                    'signature': signature
                })
            self.committed_messages.set_sent(view, sequence)


    async def prepare(self, view, sequence, request, signature):
        if not self.__is_view_valid(view) or \
            self.prepared_messages.has(view, sequence, signature):
            return

        sign_body = self.__sign_prepare_body(view, sequence, request)
        signature.validate(sign_body)


        if not await self.__prepared_message_valid(view, sequence, signature, request):
            return

        self.prepared_messages.add(view, sequence, signature, request)

        if not self.prepared_messages.has_sent(view, sequence) and await self.prepared_messages.count_sufficient(view, sequence):
            # send commit to all nodes
            my_signature = await self.__sign(sign_body)
            self.network_map.broadcast('commit', {
                'view': view,
                'sequence': sequence,
                'request': request,
                'signature': my_signature
            })
            self.prepared_messages.set_sent(view, sequence)
    
    # primary invokes this on the backups
    async def pre_prepare(self, view, sequence, request, signature):
        if not self.__is_view_valid(view) or signature.pk == self.id.pk or \
            self.accepted_pre_prepared.has(view, sequence, signature):
            return

        sign_prepare_body = self.__sign_prepare_body(view, sequence, request)
        signature.validate(sign_prepare_body)

        if not self.accepted_pre_prepared.has(view, sequence):
            my_signature = await self.__sign(sign_prepare_body)
            self.network_map.broadcast('prepare', {
                'view': view,
                'sequence': sequence,
                'request': request,
                'signature': my_signature
            })

        self.accepted_pre_prepared.add(view, sequence, signature, request)


    # only sent by primary
    async def __primary_pre_prepare(self, request):
        if not self.is_primary():
            raise(Exception('only primary does this'))

        signature = await self.__sign(self.__sign_prepare_body(self.view, self.sequence, request))
        self.network_map.broadcast('pre_prepare', {
            'view': self.view,
            'sequence': self.sequence,
            'request': request,
            'signature': signature
        })

    # sent by backups. new primary takes action
    async def view_change(self, new_view, prepared_certs, signature):
        if self.is_primary() or self.view >= new_view or \
            self.network_map.get_primary_for_view(new_view).get_pk() != self.get_pk():
            return

        signature.validate(self.__sign_view_change_body(new_view, prepared_certs))

        self.view_change_requests.add(new_view, signature, prepared_certs)
        if not await self.view_change_requests.count_sufficient(new_view):
            return

        self.__set_self_primary(new_view)

        theta = await self.view_change_requests.build_theta(new_view)

        async def sign(sequence, request):
            return await self.__sign(self.__sign_prepare_body(new_view, sequence, request))

        omicron = await self.prepared_messages.build_omicron(new_view, theta, self.get_pk(), sign)
        my_signature = await self.__sign(self.__sign_new_view_body(new_view, theta, omicron))
        self.network_map.broadcast('new_view', {
            'new_view': new_view,
            'omicron': omicron,
            'theta': theta,
            'signature': my_signature
        })

    # sent by backups when faulty timer expires
    async def __request_view_change(self):
        new_view = self.view + 1
        prepared_certs = self.prepared_messages.get_all()
        signature = await self.__sign(self.__sign_view_change_body(new_view, prepared_certs))
        self.network_map.broadcast('view_change', {
            'new_view': new_view,
            'prepared_certs': prepared_certs,
            'signature': signature
        })
       
    # sent to backups when there is a view change
    async def new_view(self, new_view, omicron, theta, signature):
        if self.get_pk() == signature.pk or self.view >= new_view or \
            self.network_map.get_primary_for_view(new_view).get_pk() != signature.pk:
            return

        signature.validate(self.__sign_new_view_body(new_view, theta, omicron))
        self.view_faulty = False
        self.view = new_view
        print(str(self.get_pk()), 'new primary:', str(signature.pk), 'view:', str(new_view))
        self.view_faulty = False
        self.primary_node = self.network_map.get_node(signature.pk)

        for entry in omicron:
            (request, signature) = omicron[entry][0], omicron[entry][1]
            await self.pre_prepare(new_view, entry, request, signature)





    

