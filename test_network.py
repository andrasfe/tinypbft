import unittest
import sys
sys.path.append(".")
from network import NetworkMap
from node import Node
from util import Signature, Request, Config
import asyncio
import time

class MockNode(Node):
    def __init__(self):
        super().__init__()
        self.calls = []
    async def client_request(self, request, signature):
        self.calls.append('client_request')
    async def pre_prepare(self, view, sequence, request, signature):
        self.calls.append('pre_prepare')
    async def prepare(self, view, sequence, request, signature):
        self.calls.append('prepare')
    async def commit(self, view, sequence, request, signature):
        self.calls.append('commit')
    def get_pk(self):
        self.calls.append('get_pk')
        return 'dummy'

class TestNetworkMap(unittest.TestCase):
    def test_NetworkMap_broadcast(self):
        nm = NetworkMap(Config(5, 3), network_delay=100)

        for i in range(5):
            nm.register_lead(MockNode(), Signature('dummy'+str(i), '34', 'aaa'))

        nm.broadcast('client_request', 
            {'request': Request('request', 123), 'signature' : Signature('12', '34', 'aaa')})

        time.sleep(5)
        nm.shutdown()

        for key in nm.get_lead_nodes():
            self.assertTrue( 'client_request' in nm.get_node(key).get_node().calls)

if __name__ == '__main__':
    tnm = TestNetworkMap()
    tnm.test_NetworkMap_broadcast()
