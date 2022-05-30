import unittest
import sys
import time
sys.path.append(".")
from node_impl import NodeImpl, NODE_TYPE
import util
import asyncio
import client
import network as nw
import json
from threading import Lock


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
key_lock = Lock()

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

    def test_with_backup_and_byzantine_node_ramp_up(self):
        REPEAT_TEST = 3
        SAMPLE_LOWER = 9
        SAMPLE_UPPER = 20
        stats = []
        for bc in range(1, 4):
            for i in range(SAMPLE_LOWER, SAMPLE_UPPER):
                byzantine_node_cnt = round(bc*i/9)

                for j in range(REPEAT_TEST):
                    key_lock.acquire()
                    counter_dict = self.test_NodeImpl_faulty_window(backup_cnt=i, request_cnt=1, byzantine_node_cnt=byzantine_node_cnt)
                    key_lock.release()
                    counter_dict['idx'] = j
                    print(counter_dict)
                    stats.append(counter_dict)
        with open("test_with_backup_and_byzantine_node_ramp_up_{}_{}_{}.json".format(SAMPLE_LOWER, SAMPLE_UPPER, round(time.time())), "w") as f:
            json.dump(stats, f)

    def test_with_fixed_backup_and_byzantine_node_ramp_up(self):
        stats = []
        for bc in range(3, 9):
            for i in range(0, 10):
                counter_dict = {}
                key_lock.acquire()
                counter_dict = self.test_NodeImpl_faulty_window(backup_cnt=9, request_cnt=1, faulty_count=3, byzantine_node_cnt=bc)
                key_lock.release()
                counter_dict['idx'] = '{}-{}'.format(bc, i)
                print(counter_dict)
                stats.append(counter_dict)
        with open("test_with_fixed_backup_and_byzantine_node_ramp_up_{}.json".format(round(time.time())), "w") as f:
            json.dump(stats, f)

    def test_NodeImpl_faulty_window(self, request_cnt = 1, faulty_count = 3, backup_cnt = 9, 
        faulty_timeout = 0, network_delay = 0, drop_ratio = 0, 
        client_patience=3, disable_primary = False, byzantine_node_cnt = 0, m=15):
        # Random: 4,39,1,2,1,5, False
        # Single: 3,10,0,0,0,1, False

        config = util.Config(faulty_timeout, faulty_count, client_patience=client_patience)
        nm = nw.NetworkMap(config, 
            network_delay=network_delay, 
            drop_ratio=drop_ratio,
            disable_primary=disable_primary,
            byzantine_node_cnt=byzantine_node_cnt)
        node1 = NodeImpl(id1, config, nm, None, NODE_TYPE.PRIMARY)
        node_stub = list(nm.get_lead_nodes().values())[0]


        for i in range(backup_cnt):
            id = util.Id('sk' + str(i), 'backup' + str(i))
            node = NodeImpl(id, config, nm, node_stub, NODE_TYPE.BACKUP)

        # nm.set_byzantine(node1.id.pk, True)

        client1 = client.Client(util.Id('666', 'client777'), config, nm)

        requests = []

        for i in range(request_cnt):
            request = util.Request('client request ' + str(time.time()), 'client777')
            requests.append(request)
            coroutine = client1.submit_request(request)
            print('request submitted:', request)
            loop.run_until_complete(coroutine)   
            time.sleep(0.5) 

        key = str(requests[0].payload)
        while m > 0 and client1.get_duration(key) is None:
            m = m - 1
            time.sleep(1)

        nm.shutdown()

        counter_dict = nm.get_counter()
        counter_dict['byzantine_node_cnt'] = nm.get_current_byzanine_cnt()
        counter_dict['f'] = config.faulty_cnt
        counter_dict['backup_cnt'] = backup_cnt + 1

        avg_duration = 0
        len_requests = len(requests)

        for request in requests:
            key = str(request.payload)
            avg_duration = client1.get_duration(key)

            if avg_duration is not None:
                avg_duration += client1.get_duration(key)
            else:
                len_requests = len_requests - 1

        if len_requests > 0:
            avg_duration = avg_duration/len_requests
        else:
            avg_duration = -1

        counter_dict['avg_duration'] = avg_duration

        return counter_dict
        
if __name__ == '__main__':
    tn = TestNode()
    # tn.test_NodeImpl_client_request()
    # print(tn.test_NodeImpl_faulty_window(faulty_timeout = 1e-5, drop_ratio = 0, network_delay = 0))

    # tn.test_with_backup_and_byzantine_node_ramp_up()

    tn.test_with_fixed_backup_and_byzantine_node_ramp_up()

    # tn.test_NodeImpl_faulty_window(request_cnt=5, faulty_timeout = 1, drop_ratio = 1, network_delay = 2, backup_cnt=39)
            
