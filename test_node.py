import unittest
import sys
import time
sys.path.append(".")
from node_impl import NodeImpl, NODE_TYPE
import util
import asyncio
import client
import network as nw


id1 = util.Id('sk123', 'primary6799')
config = util.Config(1, 2)
nm = nw.NetworkMap(config, network_delay=0)
node1 = NodeImpl(id1, config, nm, None, NODE_TYPE.PRIMARY)
node_stub = list(nm.get_lead_nodes().values())[0]

BACKUP_CNT = 10

for i in range(BACKUP_CNT):
    id = util.Id('sk' + str(i), 'backup' + str(i))
    node = NodeImpl(id, config, nm, node_stub, NODE_TYPE.BACKUP)

client1 = client.Client(util.Id('666', 'client555'), config, nm)        
client2 = client.Client(util.Id('888', 'client777'), config, nm)

loop = asyncio.get_event_loop()
class TestNode(unittest.TestCase):
    def test_NodeImpl_constructor(self):
        self.assertEqual(len(nm.lead_nodes), BACKUP_CNT + 1)

    def test_NodeImpl_client_request(self):

        node2 = list(nm.get_lead_nodes().values())[1]

        coroutine1 = client1.submit_request(util.Request('client request 1', 'client555'))
        coroutine2 = client2.submit_request(util.Request('client request 2', 'client777'))
        loop.run_until_complete(coroutine1)
        loop.run_until_complete(coroutine2)

        time.sleep(5)
        nm.shutdown()
        self.assertTrue(len(node_stub.get_node().client_requests.get_all()) > 0)
        self.assertEqual(len(node2.get_node().client_requests.get_all()), 2)

        node3 = list(nm.get_lead_nodes().values())[2]
        self.assertTrue(len(node3.get_node().prepared_messages.get_all()) > 0)

    def test_NodeImpl_faulty_window(self):
        F = 4
        BACKUP_CNT = 39
        FAULTY_TIMEOUT =1
        NETWORK_DELAY=2
        DROP_RATIO=1
        REQUEST_CNT = 5
        DISABLE_PRIMARY = False

        config = util.Config(FAULTY_TIMEOUT, F)
        nm = nw.NetworkMap(config, 
            network_delay=NETWORK_DELAY, 
            drop_ratio=DROP_RATIO,
            disable_primary=DISABLE_PRIMARY)
        node1 = NodeImpl(id1, config, nm, None, NODE_TYPE.PRIMARY)
        node_stub = list(nm.get_lead_nodes().values())[0]


        for i in range(BACKUP_CNT):
            id = util.Id('sk' + str(i), 'backup' + str(i))
            node = NodeImpl(id, config, nm, node_stub, NODE_TYPE.BACKUP)

        client1 = client.Client(util.Id('666', 'client777'), config, nm)

        for i in range(REQUEST_CNT):
            coroutine = client1.submit_request(util.Request('client request ' + str(i), 'client777'))
            loop.run_until_complete(coroutine)   
            time.sleep(0.5) 

        time.sleep(5)
        nm.shutdown()

        print('total messages', nm.get_counter())
        
if __name__ == '__main__':
    tn = TestNode()
    # tn.test_NodeImpl_client_request()
    tn.test_NodeImpl_faulty_window()