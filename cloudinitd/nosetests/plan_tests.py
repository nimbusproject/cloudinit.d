import cloudinitd
import cloudinitd.nosetests
from cloudinitd.user_api import CloudInitD
import tempfile
import logging



import unittest
import os

class PlanTests(unittest.TestCase):

    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
        cloudinitd.close_log_handlers()

    def test_lotsonlevel(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/plantest1/top/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)
        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)
        fname = cb.get_db_file()
        os.remove(fname)

if __name__ == '__main__':
    unittest.main()
