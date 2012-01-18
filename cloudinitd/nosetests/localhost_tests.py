import tempfile
import unittest
from unittest.case import SkipTest
import uuid
from cloudinitd.cb_iaas import iaas_get_con
from cloudinitd.statics import get_remote_working_dir
from cloudinitd.user_api import CloudInitD
import os
import cloudinitd
import cloudinitd.cli.boot
import  time



class CloudInitDLocalhostTests(unittest.TestCase):

    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
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

    def _tst_local_host(self):
        cmd = "ssh  -n -T -o BatchMode=yes -o StrictHostKeyChecking=no -o PasswordAuthentication=no localhost /bin/true"
        rc = os.system(cmd)
        if rc != 0:
            raise SkipTest()

    def _basic_directory_created(self):

        self._tst_local_host()

        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/localhost/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)

        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)

        wd = get_remote_working_dir()
        rc = os.path.exists(wd)
        self.assertTrue(rc, "The directory %s should exist" % (wd))

        print "cleanup"
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

        rc = os.path.exists(wd)
        self.assertTrue(rc, "Thdirectory %s should NOT exist" % (wd))

    def test_default_directory_created(self):
        self._basic_directory_created()

    def test_new_directory_created(self):
        os.environ['REMOTE_WORKING_DIR_ENV_STR'] = "/tmp/" + str(uuid.uuid4())
        try:
            self._basic_directory_created()
        finally:
            del os.environ['REMOTE_WORKING_DIR_ENV_STR']