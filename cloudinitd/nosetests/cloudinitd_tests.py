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



class CloudInitDTests(unittest.TestCase):

    def setUp(self):
        self.bkfab  = None
        self.bkssh = None
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        if 'CLOUDBOOT_TESTENV' in os.environ:
            self.bkfab = os.environ['CLOUD_BOOT_FAB']
            self.bkssh = os.environ['CLOUD_BOOT_SSH']


    def tearDown(self):
        if self.bkfab:
            os.environ['CLOUD_BOOT_FAB'] = self.bkfab
            os.environ['CLOUD_BOOT_SSH'] = self.bkssh


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

    def test_basic(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/terminate/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)

        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "status",  "%s" % (runname)])
        self.assertEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def test_list_commands(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "commands"])
        self.assertEqual(rc, 0)

    def test_help(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["--help"])
        self.assertEqual(rc, 0)        

    def test_basic_validate(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile,  "--validate", "boot",  "%s/simplebadplan/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertNotEqual(rc, 0)
        
    def test_bad_validate(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile,  "--validate", "boot",  "%s/baddeps/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertNotEqual(rc, 0)

    def test_validate_nolaunch(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)

        key = None
        secret = None
        try:
            key = os.environ['CLOUDBOOT_IAAS_ACCESS_KEY']
            secret = os.environ['CLOUDBOOT_IAAS_SECRET_KEY']
        except:
            pass

        # XXX this test may fail for nimbus
        con = cloudinitd.cb_iaas.iaas_get_con(None, key=key, secret=secret)
        i_list = con.get_all_instances()
        rc = cloudinitd.cli.boot.main(["-O", outfile, "--validate", "boot",  "%s/badlevels/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertNotEqual(rc, 0)
        after_list = con.get_all_instances()
        self.assertEqual(len(i_list), len(after_list))


    def _get_runname(self, fname):
        n = "Starting up run"
        line = self._find_str(fname, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)
        return runname

    def test_list_simple(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/terminate/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)

        runname = self._get_runname(outfile)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "list"])
        self.assertEqual(rc, 0)
        line = self._find_str(outfile, runname)
        self.assertNotEqual(line, None)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def test_cleanup_list(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/terminate/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)

        runname = self._get_runname(outfile)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "list"])
        self.assertEqual(rc, 0)
        line = self._find_str(outfile, runname)
        self.assertEqual(line, None)

    def test_reboot_simple(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "-l", "info", "boot",  "%s/terminate/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        runname = self._get_runname(outfile)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "-l", "debug", "reboot",  "%s" % (runname)])
        self.assertEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "status",  "%s" % (runname)])
        self.assertEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def bad_name_tests(self):
        runname = str(uuid.uuid4()).split("-")[0]
        rc = cloudinitd.cli.boot.main(["status",  "%s" % (runname)])
        self.assertNotEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["terminate",  "%s" % (runname)])
        self.assertNotEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["reboot",  "%s" % (runname)])
        self.assertNotEqual(rc, 0)

    def check_boot_output_test(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-v","-v","-v","-v", "-O", outfile, "boot",  "%s/terminate/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        runname = self._get_runname(outfile)

        n = "instance:"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        n = "hostname:"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)

        n = "SUCCESS"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def check_status_output_test(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/terminate/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        runname = self._get_runname(outfile)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v","-v","-v","-v", "status", runname])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        n = "instance:"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        n = "hostname:"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)

        n = "SUCCESS"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def check_terminate_output_test(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/terminate/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        runname = self._get_runname(outfile)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v", "-v", "-v", "terminate",  "%s" % (runname)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        n = "instance:"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        ndx = line.find("None")
        self.assertTrue(ndx >= 0)
        n = "hostname:"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        ndx = line.find("None")
        self.assertTrue(ndx >= 0)

        n = "SUCCESS"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)

    def check_status_shutdown_error_test(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        dir = os.path.expanduser("~/.cloudinitd/")
        conf_file = self.plan_basedir + "/terminate/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)
        runname = cb.run_name
        svc = cb.get_service("sampleservice")
        p = svc.shutdown()
        rc = p.poll()
        while not rc:
            rc = p.poll()
            time.sleep(0.1)

        if 'CLOUDBOOT_TESTENV' in os.environ:
            bkfab = os.environ['CLOUD_BOOT_FAB']
            bkssh = os.environ['CLOUD_BOOT_SSH']
            os.environ['CLOUD_BOOT_FAB'] = "/bin/false"
            os.environ['CLOUD_BOOT_SSH'] = "/bin/false"

        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v","-v","-v","-v", "status", runname])
        if 'CLOUDBOOT_TESTENV' in os.environ:
            os.environ['CLOUD_BOOT_FAB'] = bkfab
            os.environ['CLOUD_BOOT_SSH'] = bkssh
        self._dump_output(outfile)
        n = "ERROR"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def check_status_error_test(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        dir = os.path.expanduser("~/.cloudinitd/")
        conf_file = self.plan_basedir + "/terminate/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)
        runname = cb.run_name
        svc = cb.get_service("sampleservice")

        secret = svc.get_attr_from_bag('iaas_secret')
        key = svc.get_attr_from_bag('iaas_key')
        iaas_host = svc.get_attr_from_bag('iaas_hostname')
        iaas_port = svc.get_attr_from_bag('iaas_port')
        instance_id = svc.get_attr_from_bag('instance_id')
        con = iaas_get_con(None, key=key, secret=secret, iaashostname=iaas_host, iaasport=iaas_port)
        instance = con.find_instance(instance_id)
        instance.terminate()

        if 'CLOUDBOOT_TESTENV' in os.environ:
            bkfab = os.environ['CLOUD_BOOT_FAB']
            bkssh = os.environ['CLOUD_BOOT_SSH']
            os.environ['CLOUD_BOOT_FAB'] = "/bin/false"
            os.environ['CLOUD_BOOT_SSH'] = "/bin/false"

        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v","-v","-v","-v", "status", runname])
        if 'CLOUDBOOT_TESTENV' in os.environ:
            os.environ['CLOUD_BOOT_FAB'] = bkfab
            os.environ['CLOUD_BOOT_SSH'] = bkssh
        self._dump_output(outfile)
        n = "ERROR"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def check_repair_error_test(self):
        if 'CLOUDBOOT_TESTENV' in os.environ:
            # we cannot run this one in fake mode yet
            return
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        dir = os.path.expanduser("~/.cloudinitd/")
        conf_file = self.plan_basedir + "/multileveldeps/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)
        runname = cb.run_name
        svc = cb.get_service("l2service")

        secret = svc.get_attr_from_bag('iaas_secret')
        key = svc.get_attr_from_bag('iaas_key')
        iaas_host = svc.get_attr_from_bag('iaas_hostname')
        iaas_port = svc.get_attr_from_bag('iaas_port')
        instance_id = svc.get_attr_from_bag('instance_id')
        con = iaas_get_con(svc._svc, key=key, secret=secret, iaashostname=iaas_host, iaasport=iaas_port)
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

    def test_multiterminate(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/oneservice/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname1 = line[len(n):].strip()

        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/oneservice/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname2 = line[len(n):].strip()

        print "run name is %s and %s" % (runname1, runname2)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  runname1, runname2])
        self.assertEqual(rc, 0)