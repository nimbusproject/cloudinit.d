import time
import unittest
import cloudinitd
import cloudinitd.nosetests
from cloudinitd.exceptions import APIUsageException
from cloudinitd.user_api import CloudInitD
import tempfile
import os




class ManyAtOnceTests(unittest.TestCase):
    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
        cloudinitd.close_log_handlers()

    def _start_one(self, conf_file):

        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/" + conf_file + "/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)
        return (dir, cb)

    def _simple_test(self, conf_file):

        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/oneservice/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)
        return (dir, cb)

    def _status(self, dir, run_name):
        cb = CloudInitD(dir, db_name=run_name, terminate=False, boot=False, ready=True, continue_on_error=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)

    def _terminate(self, dir, run_name):
        cb = CloudInitD(dir, db_name=run_name, terminate=True, boot=False, ready=False, continue_on_error=True)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)
        fname = cb.get_db_file()
        os.remove(fname)

    def test_kill_first_level(self):
        tst_name = "multilevelsimple"
        (dir, cb) = self._start_one(tst_name)
        svc = cb.get_service("Two")
        p = svc.shutdown()
        rc = p.poll()
        while not rc:
            rc = p.poll()
            time.sleep(0.1)
        self._status(dir, cb.run_name)
        self._terminate(dir, cb.run_name)

    def test_get_service(self):
        tst_name = "multilevelsimple"
        (dir, cb) = self._start_one(tst_name)
        svc = cb.get_service("Two")
        h = svc.get_attr_from_bag("hostname")
        print h
        self._terminate(dir, cb.run_name)

    def test_getlevels(self):
        tst_name = "multilevelsimple"
        (dir, cb) = self._start_one(tst_name)
        for i in range(0, cb.get_level_count()):
            cb.get_level(i)
        self._terminate(dir, cb.run_name)

    def test_restart_one_level(self):
        tst_name = "oneservice"
        (dir, cb) = self._start_one(tst_name)
        svc = cb.get_service("sampleservice")
        p = svc.restart()
        rc = p.poll()
        while not rc:
            rc = p.poll()
            time.sleep(0.1)
        self._status(dir, cb.run_name)
        self._terminate(dir, cb.run_name)

if __name__ == '__main__':
    unittest.main()
