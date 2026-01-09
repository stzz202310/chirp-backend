from gatekeeper.models import GateKeeper
from testing.testcases import TestCase


class GatekeeperTests(TestCase):

    def setUp(self):
        # super(GatekeeperTests, self).setUp()
        self.clear_cache()

    def test_gatekeeper(self):
        gk = GateKeeper.get(gk_name='gk_name')
        self.assertEqual(gk, {'percent': 0, 'description': ''})
        self.assertEqual(GateKeeper.is_switch_on(gk_name='gk_name'), False)
        self.assertEqual(GateKeeper.in_gk(gk_name='gk_name', user_id=1), False)

        GateKeeper.set_kv(gk_name='gk_name', key='percent', value=20)
        gk = GateKeeper.get(gk_name='gk_name')
        self.assertEqual(gk, {'percent': 20, 'description': ''})
        self.assertEqual(GateKeeper.is_switch_on(gk_name='gk_name'), False)
        self.assertEqual(GateKeeper.in_gk(gk_name='gk_name', user_id=1), True)

        GateKeeper.set_kv(gk_name='gk_name', key='percent', value=100)
        self.assertEqual(GateKeeper.is_switch_on(gk_name='gk_name'), True)
        self.assertEqual(GateKeeper.in_gk(gk_name='gk_name', user_id=1), True)