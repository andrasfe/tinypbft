import unittest
import sys
sys.path.append(".")
from node_impl import NodeImpl, NODE_TYPE
import util
import time
import network as nw

class TestUtil(unittest.TestCase):
    def test_signature(self):
        sign = util.Signature('1234', '4567', 'this is the data')
        try:
            sign.validate('this is the data')
        except:
            self.fail('should not throw')

    def test_id(self):
        id = util.Id('123', '456')
        sign = id.sign('some data')
        try:
            sign.validate('some data')
        except:
            self.fail('should not throw')

    def test_ViewSequenceState(self):
        vss = util.ViewSequenceState()

        for i in range(5):
            vs = util.ViewSequence(i, 1, 'some request')
            vss.add(vs)

        self.assertEqual(len(vss.state.keys()), 5)

    def test_AcceptedPrePrepared(self):
        ars = util.AcceptedPrePrepared()
        ars.add(1, 2, 'some stuff', '1234')

        try:
            ars.add(1, 2, 'some other stuff', '1234')
            self.assertFalse('should have failed')
        except:
            self.assertTrue('handled correctly')

    def test_ClientRequests(self):
        config = util.Config(1, 2)
        crt = util.ClientRequests(config)
        request = util.Request('some request', '5555')
        crt.add(request, '5555')
        time.sleep(2)

        self.assertTrue(crt.timer_faulty(request, '5555'))
        try:
            crt.timer_faulty(util.Request('some other request', '3456'))
            self.assertFalse('should have failed')
        except:
            self.assertTrue('handled correctly')

    def test_PreparedMessages(self):
        pm = util.PreparedMessages(util.Config(1, 2))
        pm.add(1, 1, '1234', 'c1')
        pm.add(1, 2, '1234', 'c2')
        pm.add(1, 3, '3343', 'c3')
        pm.add(1, 4, '5567', 'c4')
        pm.add(1, 5, '6678', 'c5')
        pm.add(2, 5, '1234', 'c6')

        pks = pm.get_all()

        self.assertEqual(len(pks), 6)


if __name__ == '__main__':
    TestUtil().test_ClientRequests()
