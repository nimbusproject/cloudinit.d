import tempfile
import unittest
import uuid
from cloudinitd.cb_iaas import iaas_get_con
from cloudinitd.user_api import CloudInitD
import os
import cloudinitd
import cloudinitd.cli.boot
import  time
__author__ = 'bresnaha'



class OutputJsonTests(unittest.TestCase):

    def setUp(self):
        pass


    def tearDown(self):
        pass


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

    def test_basic(self):
        if 'CLOUDBOOT_TESTENV' in os.environ:
            return
        
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/outputdep/top.conf" % (cloudinitd.nosetests.g_plans_dir)])
        self.assertEqual(rc, 0)

        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

