import tempfile
import unittest
import uuid
from cloudinitd.cb_iaas import iaas_get_con
from cloudinitd.user_api import CloudInitD
import os
import cloudinitd
import cloudinitd.cli.boot
import  time




class ManyTerminateHangTests(unittest.TestCase):

    def setUp(self):
        self.bkfab  = None
        self.bkssh = None
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        if 'CLOUDINITD_TESTENV' in os.environ:
            self.bkfab = os.environ['CLOUDINITD_FAB']
            self.bkssh = os.environ['CLOUDINITD_SSH']


    def tearDown(self):
        if self.bkfab:
            os.environ['CLOUDINITD_FAB'] = self.bkfab
            os.environ['CLOUDINITD_SSH'] = self.bkssh
        cloudinitd.close_log_handlers()


    def _find_str(self, filename, needle):

        file = open(filename, "r")
        try:
            found = False
            while not found:
                line = file.readline()
                if not line:
                    return None
                ndx = line.find(needle)
                if ndx >= 0:
                    return line
        finally:
            file.close()

    def _dump_output(self, filename):
        file = open(filename, "r")
        print file.readlines()
        file.close()

    def test_back2back_terminate_simple(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/back2backterminatehang//top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)

        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "--noclean", "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

