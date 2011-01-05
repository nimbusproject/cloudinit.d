import time
import unittest
from cloudboot.user_api import CloudBoot
import tempfile
import os

__author__ = 'bresnaha'


class InstanceDiesTests(unittest.TestCase):
    def _start_one(self, conf_file):
        self.plan_basedir = os.environ['CLOUDBOOT_TEST_PLAN_DIR']
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/" + conf_file + "/top.conf"
        cb = CloudBoot(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)
        return (dir, cb)

    def _status(self, dir, run_name):
        cb = CloudBoot(dir, db_name=run_name, terminate=False, boot=False, ready=True, continue_on_error=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)

    def _terminate(self, dir, run_name):
        cb = CloudBoot(dir, db_name=run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)
        fname = cb.get_db_file()
        os.remove(fname)

    def test_nokill(self):
        tst_name = "multilevelsimple"
        (dir, cb) = self._start_one(tst_name)
        self._status(dir, cb.run_name)
        self._terminate(dir, cb.run_name)

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

if __name__ == '__main__':
    unittest.main()
