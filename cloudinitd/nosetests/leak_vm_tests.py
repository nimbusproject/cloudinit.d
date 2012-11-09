import tempfile
import unittest
import uuid
from cloudinitd.cb_iaas import iaas_get_con
from cloudinitd.user_api import CloudInitD
import os
import cloudinitd
import cloudinitd.cli.boot
import  time




class LeakRepairTests(unittest.TestCase):

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

    def test_repair_leaks(self):

        if 'CLOUDINITD_TESTENV' in os.environ:
            #this wont work in fake mode
            return

        key = None
        secret = None
        url= None

        try:
            key = os.environ['CLOUDINITD_IAAS_ACCESS_KEY']
            secret = os.environ['CLOUDINITD_IAAS_SECRET_KEY']
            url = os.environ['CLOUDINITD_IAAS_URL']
        except:
            pass

        # XXX this test may fail for nimbus
        con = cloudinitd.cb_iaas.iaas_get_con(None, key=key, secret=secret, iaasurl=url)
        i_list = con.get_all_instances()
        initial_list = [i for i in i_list if i.get_state() == "running"]

        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        print "booting the bad plan"
        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v", "-v", "-v", "boot",  "%s/reloadplan/badtop.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)
        self.assertNotEqual(rc, 0)

        print "repair bad plan"
        rc = cloudinitd.cli.boot.main(["repair",  runname])
        self.assertNotEqual(rc, 0)

        print "reload a good plan"
        rc = cloudinitd.cli.boot.main(["--name", runname, "reload",  "%s/reloadplan/goodtop.conf" % (self.plan_basedir)])
        self.assertEqual(rc, 0)
        print "repair the good plan"
        rc = cloudinitd.cli.boot.main(["repair",  runname])
        self.assertEqual(rc, 0)
        print "terminate"
        rc = cloudinitd.cli.boot.main(["terminate",  runname])
        self.assertEqual(rc, 0)

        p_list = con.get_all_instances()
        post_list = [i for i in p_list if i.get_state() == "running"]

        self.assertEqual(len(post_list), len(initial_list))

    def _get_runname(self, fname):
        n = "Starting up run"
        line = self._find_str(fname, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)
        return runname
