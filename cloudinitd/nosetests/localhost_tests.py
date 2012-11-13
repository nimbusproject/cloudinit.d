from datetime import datetime
import tempfile
import unittest
from unittest.case import SkipTest
import uuid
from cloudinitd.statics import get_remote_working_dir
import os
import cloudinitd
import cloudinitd.cli.boot


class CloudInitDLocalhostTests(unittest.TestCase):

    def setUp(self):
        self._test_fab = None
        self._test_ssh = None
        if 'CLOUDINITD_SSH' in os.environ:
            self._test_ssh = os.environ['CLOUDINITD_SSH']
            del os.environ['CLOUDINITD_SSH']
        if 'CLOUDINITD_FAB' in os.environ:
            self._test_fab = os.environ['CLOUDINITD_FAB']
            del os.environ['CLOUDINITD_FAB']
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
        if self._test_fab:
            os.environ['CLOUDINITD_FAB'] = self._test_fab
        if self._test_ssh:
            os.environ['CLOUDINITD_SSH'] = self._test_ssh
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
        cmd = "ssh  -n -T -o BatchMode=yes -o StrictHostKeyChecking=no -o PasswordAuthentication=no localhost true"
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
        self.assertTrue(rc, "The directory %s should NOT exist" % (wd))

    def test_default_directory_created(self):
        self._basic_directory_created()

    def test_new_directory_created(self):
        os.environ['REMOTE_WORKING_DIR_ENV_STR'] = "/tmp/" + str(uuid.uuid4())
        try:
            self._basic_directory_created()
        finally:
            del os.environ['REMOTE_WORKING_DIR_ENV_STR']

    def test_boot_timeout(self):

        self._tst_local_host()

        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-vvv", "-O", outfile, "boot",  "%s/localhost_to/boot_to_top.conf" % (self.plan_basedir)])
        #cmd = "/home/bresnaha/pycharmVE/bin/cloudinitd -l debug -vvv -O %s boot %s/localhost_to/boot_to_top.conf" % (outfile, self.plan_basedir)
        #rc = os.system(cmd)
        self._dump_output(outfile)
        print rc

        try:
            n = "Starting up run"
            line = self._find_str(outfile, n)
            self.assertNotEqual(line, None)
            runname = line[len(n):].strip()
            print "run name is %s" % (runname)
            self.assertNotEqual(rc, 0)
        finally:
            cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])

    def test_terminate_timeout(self):

        self._tst_local_host()

        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/localhost_to/terminate_to_top.conf" % (self.plan_basedir)])
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
        start = datetime.now()
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        end = datetime.now()
        self.assertNotEqual(rc, 0, "terminate now will return non 0 values")

        diff = end - start
        self.assertLess(diff.seconds, 50)

    def test_ready_timeout(self):

        self._tst_local_host()

        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/localhost_to/ready_to_top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)

        try:
            n = "Starting up run"
            line = self._find_str(outfile, n)
            self.assertNotEqual(line, None)
            runname = line[len(n):].strip()
            print "run name is %s" % (runname)
            self.assertNotEqual(rc, 0)
        finally:
            cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
