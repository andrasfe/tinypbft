import time
import sys
from threading import Lock
sys.path.append(".")
import node
import random

class NodeStub(node.Node):
    def __init__(self, node, config = None, network_delay = 0, disable_primary = False, drop_ratio = 0, byzantine = False):
        self.node = node
        self.network_delay = network_delay
        self.drop_ratio = drop_ratio
        self.config = config
        self.disable_primary = disable_primary
        self._key_lock = Lock()
        # just want to know when we initialize
        self.primary = node.is_primary()
        self.byzantine = byzantine

    def get_node(self):
        return self.node

    def get_pk(self):
        return self.node.get_pk()

    def is_primary(self):
        return self.node.is_primary()

    def __random_drop(self, drop_primary = False):
        if drop_primary and self.disable_primary and self.primary:
            return True if random.randint(1, 10) < 5 else False
        elif self.drop_ratio > 0 and random.randint(1, 1000) <= self.drop_ratio:
            print('↓', self.get_pk())
            return True
        return False

    def __random_sleep(self, times = 1):
        if self.network_delay == 0:
            return

        time.sleep(times*random.randint(0, self.network_delay)/1000)

    async def client_request(self, request, signature):
        if self.byzantine or self.__random_drop(True):
            return

        await self.node.client_request(request, signature)


    async def pre_prepare(self, view, sequence, request, signature):
        if self.byzantine or self.__random_drop():
            return

        self.__random_sleep()
        self._key_lock.acquire()
        await self.node.pre_prepare(view, sequence, request, signature)
        self._key_lock.release()

    async def prepare(self, view, sequence, request, signature):
        if self.byzantine or self.__random_drop():
            return

        self.__random_sleep()
        self._key_lock.acquire()
        await self.node.prepare(view, sequence, request, signature)
        self._key_lock.release()


    async def commit(self, view, sequence, request, signature):
        if self.byzantine or self.__random_drop():
            return

        self.__random_sleep()
        self._key_lock.acquire()
        await self.node.commit(view, sequence, request, signature)
        self._key_lock.release()

    async def view_change(self, new_view, prepared_certs, signature):
        if self.byzantine or self.__random_drop():
            return

        self.__random_sleep()
        self._key_lock.acquire()
        await self.node.view_change(new_view, prepared_certs, signature)
        self._key_lock.release()    

    async def new_view(self, new_view, omicron, theta, signature):
        if self.byzantine or self.__random_drop():
            return

        self.__random_sleep()
        self._key_lock.acquire()
        await self.node.new_view(new_view, omicron, theta, signature)
        self._key_lock.release()    
  
    