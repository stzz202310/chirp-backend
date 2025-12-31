from gatekeeper.models import Gatekeeper
from testing.testcases import TestCase


class GatekeeperTests(TestCase):

    def setUp(self):
        # super(GatekeeperTests, self).setUp()
        self.clear_cache()

    def test_gatekeeper(self):
        gk = Gatekeeper.get(gk_name='gk_name')
        self.assertEqual(gk, {'percent': 0, 'description': ''})
        self.assertEqual(Gatekeeper.is_switch_on(gk_name='gk_name'), False)
        self.assertEqual(Gatekeeper.in_gk(gk_name='gk_name', user_id=1), False)

        Gatekeeper.set_kv(gk_name='gk_name', key='percent', value=20)
        gk = Gatekeeper.get(gk_name='gk_name')
        self.assertEqual(gk, {'percent': 20, 'description': ''})
        self.assertEqual(Gatekeeper.is_switch_on(gk_name='gk_name'), False)
        self.assertEqual(Gatekeeper.in_gk(gk_name='gk_name', user_id=1), True)

        Gatekeeper.set_kv(gk_name='gk_name', key='percent', value=100)
        self.assertEqual(Gatekeeper.is_switch_on(gk_name='gk_name'), True)
        self.assertEqual(Gatekeeper.in_gk(gk_name='gk_name', user_id=1), True)