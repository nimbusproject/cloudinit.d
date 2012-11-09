import cloudinitd
import cloudinitd.nosetests
from cloudinitd.user_api import CloudInitD
import tempfile
import unittest
import os

class BasicUserAPITests(unittest.TestCase):

    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
        cloudinitd.close_log_handlers()

    def _start_one(self, conf_file):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/" + conf_file + "/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)

        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)
        fname = cb.get_db_file()
        os.remove(fname)

    def test_lotsonlevel(self):
        tst_name = "lotsonlevel"
        self._start_one(tst_name)

    def test_multileveldeps(self):
        tst_name = "multileveldeps"
        self._start_one(tst_name)

    def test_multilevelsimple(self):
        tst_name = "multilevelsimple"
        self._start_one(tst_name)

    def test_oneservice(self):
        tst_name = "oneservice"
        self._start_one(tst_name)

    def test_simplelevels(self):
        tst_name = "simplelevels"
        self._start_one(tst_name)

    def test_terminate(self):
        tst_name = "terminate"
        self._start_one(tst_name)

    def test_cloudconf(self):
        tst_name = "cloudconf"
        self._start_one(tst_name)

    def test_localexe(self):
        tst_name = "localhostexe"
        self._start_one(tst_name)

if __name__ == '__main__':
    unittest.main()
