import cloudinitd
import cloudinitd.nosetests
from cloudinitd.user_api import CloudInitD
import tempfile
import logging



import time
import unittest
import os

class TenLevelsTests(unittest.TestCase):

    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
        cloudinitd.close_log_handlers()

    def test_badlevel_bootpgm(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/tenlevels/top.conf"
        pass_ex = True
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)

        # XXX NOTE.  Here we take advantage of some internal knowledge.  if variable names change
        # this test could fail
        bootorder = cb._bo
        self.assertEqual(10, len(bootorder.levels))

        names = {0: "one", 1 : "two", 2 : "three", 3: "four", 4: "five", 5: "six", 6: "seven", 7: "eight", 8: "nine", 9: "ten"}
        for i in range(len(bootorder.levels)):
            l = bootorder.levels[i]
            svc = l.services[0]
            self.assertEqual(svc.name, names[i], "the string %s and %s should be the same for level %d" % (svc.name, names[i], i))

if __name__ == '__main__':
    unittest.main()
