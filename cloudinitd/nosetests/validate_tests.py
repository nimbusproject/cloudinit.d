import cloudinitd
import cloudinitd.nosetests
from cloudinitd.user_api import CloudInitD
import tempfile
import logging



import unittest
import os

class ValidateTests(unittest.TestCase):

    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
        cloudinitd.close_log_handlers()

    def test_validateiaas(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/iaastypevalidate/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()

        cb.block_until_complete(poll_period=1.0)

        # check the log for a warning
        fname = os.path.expanduser("~/.cloudinitd/%s/badsvc.log" % (cb.run_name))
        print fname
        self.assertTrue(os.path.exists(fname), "The path %s should exist" % (fname))
        f = open(fname, "r")
        found = False
        for l in f.readlines():
            print l
            ndx = l.find("WARN")
            if ndx >= 0:
                ndx = l.find("2.7")
                if ndx >= 0:
                    found = True
        self.assertTrue(found, "a warning with the key 2.7 should be in the logfile %s" %(fname))
        f.close()

        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)
        fname = cb.get_db_file()
        os.remove(fname)

if __name__ == '__main__':
    unittest.main()
