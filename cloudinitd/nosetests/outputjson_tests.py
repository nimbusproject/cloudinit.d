import tempfile
import unittest
import uuid
from cloudinitd.cb_iaas import iaas_get_con
from cloudinitd.user_api import CloudInitD
import os
import cloudinitd
import cloudinitd.cli.boot
import  time




class OutputJsonTests(unittest.TestCase):

    def setUp(self):
        pass


    def tearDown(self):
        cloudinitd.close_log_handlers()

    def _dump_output(self, filename):
        file = open(filename, "r")
        print file.readlines()
        file.close()

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
        if 'CLOUDINITD_TESTENV' in os.environ:
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

    def check_repair_error_test(self):
        if 'CLOUDINITD_TESTENV' in os.environ:
            # we cannot run this one in fake mode yet
            return
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        dir = os.path.expanduser("~/.cloudinitd/")
        conf_file = "%s/outputdep/top.conf" % (cloudinitd.nosetests.g_plans_dir)
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)
        runname = cb.run_name
        svc = cb.get_service("onelvl1")

        secret = svc.get_attr_from_bag('iaas_secret')
        key = svc.get_attr_from_bag('iaas_key')
        iaas_url= svc.get_attr_from_bag('iaas_url')
        instance_id = svc.get_attr_from_bag('instance_id')
        con = iaas_get_con(svc._svc, key=key, secret=secret, iaasurl=iaas_url)
        instance = con.find_instance(instance_id)
        instance.terminate()

        print "start repair"
        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v","-v","-v","repair", runname])
        self._dump_output(outfile)
        n = "ERROR"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)

        print "start terminate"
        rc = cloudinitd.cli.boot.main(["terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)
