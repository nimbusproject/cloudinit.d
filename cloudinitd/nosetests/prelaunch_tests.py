import cloudinitd
import cloudinitd.nosetests
import cloudinitd.cb_iaas
from cloudinitd.user_api import CloudInitD
import tempfile
import logging



import unittest
import os

class PrelaunchTests(unittest.TestCase):

    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
        cloudinitd.close_log_handlers()

    def test_prelaunch(self):

        key = None
        secret = None
        url = None
        try:
            key = os.environ['CLOUDINITD_IAAS_ACCESS_KEY']
            secret = os.environ['CLOUDINITD_IAAS_SECRET_KEY']
            url = os.environ['CLOUDINITD_IAAS_URL']
        except:
            pass

        # XXX this test may fail for nimbus
        con = cloudinitd.cb_iaas.iaas_get_con(None, key=key, secret=secret, iaasurl=url)
        i_list = con.get_all_instances()
        conf_file = "multilevelsimple"
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/" + conf_file + "/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.pre_start_iaas()

        post_boot_list = con.get_all_instances()

        self.assertNotEqual(len(i_list), len(post_boot_list), "The list of instances should have grown")
        self.assertTrue(len(i_list)+3 < len(post_boot_list), "The list of instances should have grown by more than the number of services in the first level")

        cb.start()
        post_start_list = con.get_all_instances()
        self.assertEqual(len(post_boot_list), len(post_start_list), "The list should not have grown")
        cb.block_until_complete(poll_period=1.0)

        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)
        fname = cb.get_db_file()
        os.remove(fname)


if __name__ == '__main__':
    unittest.main()
