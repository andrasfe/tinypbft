import imp
import time
import random
from node_stub import NodeStub
import asyncio
from threading import Thread, Lock
import queue
import sys
import logging

THREAD_COUNT = 10
STR_SEPARATOR = ','

class Task:
    def __init__(self, node, function_name, args):
        self.node = node
        self.function_name = function_name
        self.args = args

    def __str__(self) -> str:
        ret = self.node.get_pk() + STR_SEPARATOR + \
            self.function_name + STR_SEPARATOR + str(self.args) + STR_SEPARATOR

        for key in self.args:
            ret += str(key) + ':' + str(self.args[key]) + STR_SEPARATOR

        return ret

class NetworkMap:
    def __init__(self, config, network_delay = 0, drop_ratio = 0, disable_primary = False, byzantine_node_cnt = 0) -> None:
        self.config = config
        self.lead_nodes = {}
        self.client_nodes = {}
        self.network_delay = network_delay
        self.drop_ratio = drop_ratio
        self.disable_primary = disable_primary
        self._key_lock = Lock()
        self._counter = dict()
        self.tasks = queue.Queue()
        self.stop = False
        self.workers = []
        self.byzantine_node_cnt = byzantine_node_cnt
        self.current_byzantine_cnt = 0

        for i in range(THREAD_COUNT):
            worker = Thread(target=self.__send_events, daemon=True)
            worker.start()
            self.workers.append(worker)

    def random_sleep(self):
        if self.network_delay == 0:
            return

        time.sleep(random.randint(0, self.network_delay)/1000)

    def set_network_delay(self, network_delay):
        self.network_delay = network_delay

    def register_lead(self, node, signature):
        is_byzantine = random.randint(1, 3) == 2 and self.byzantine_node_cnt > self.current_byzantine_cnt

        if is_byzantine:
            self.current_byzantine_cnt += 1
            

        signature.validate('aaa')
        self.lead_nodes[signature.pk] = NodeStub(node, config=self.config, network_delay=self.network_delay, \
            disable_primary = self.disable_primary, drop_ratio=self.drop_ratio, byzantine=is_byzantine)

    def set_byzantine(self, key, new_value):
        self.lead_nodes[key].set_byzantine(new_value)

    def register_client(self, node, signature):
        signature.validate('some data')
        self.client_nodes[signature.pk] = node

    def get_lead_nodes(self):
        self.random_sleep()
        return self.lead_nodes

    def get_node(self, pk):
        return self.client_nodes[pk] if pk in self.client_nodes else self.lead_nodes[pk] 

    def get_primary_for_view(self, new_view):
        node_list = list(self.lead_nodes.values())
        return node_list[new_view % len(node_list)]


    # this helps when running synchronously
    def get_shuffled_lead_nodes(self):
        self.random_sleep()
        shuffled_list = list(self.lead_nodes.values())
        random.shuffle(shuffled_list)
        return shuffled_list

    def broadcast(self, function_name, args):
        self._key_lock.acquire()
        for node in self.get_shuffled_lead_nodes():
            # exclude the sender. 
            signature = args['signature']

            if signature.pk == node.get_pk():
                continue

            self.tasks.put(Task(node, function_name, args))
        self._key_lock.release()

    def send_to_node(self, node, function_name, args):
        self._key_lock.acquire()
        self.tasks.put(Task(node, function_name, args))
        self._key_lock.release()

    def send_to_primary_for_view(self, view, function_name, args):
        node = self.get_primary_for_view(view)
        self.send_to_node(node, function_name, args)


    def __send_events(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            if self.tasks.empty():
                if self.is_shutdown():
                    sys.exit()
                else:
                    time.sleep(2)
                    continue
            task = self.tasks.get()
            coroutine = getattr(task.node, task.function_name)(**task.args)
            self.__incr(task.function_name)
            loop.run_until_complete(coroutine)
            self.tasks.task_done()

    def is_shutdown(self):
        out = None
        self._key_lock.acquire()
        out = self.stop
        self._key_lock.release()
        return out


    def shutdown(self):
        self._key_lock.acquire()
        self.stop = True
        self._key_lock.release()

    def __incr(self, function_name):
        self._key_lock.acquire()
        self._counter[function_name] = self._counter.get(function_name, 0) + 1
        self._key_lock.release()

    def get_counter(self):
        return self._counter


    



