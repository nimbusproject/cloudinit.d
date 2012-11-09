import tempfile
import unittest
import uuid
from cloudinitd.cb_iaas import iaas_get_con
from cloudinitd.user_api import CloudInitD
import os
import cloudinitd
import cloudinitd.cli.boot
import  time




class CloudInitDTests(unittest.TestCase):

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

    def test_terminate_variable(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/terminate_variable/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)

        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)
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

    def test_bad_files(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile,  "--validate", "boot",  "%s/badfiles/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertNotEqual(rc, 0)

    def test_bad_validate(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile,  "--validate", "boot",  "%s/baddeps/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertNotEqual(rc, 0)

    def test_bad_dryrun(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile,  "--dryrun", "boot",  "%s/baddeps/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertNotEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/baddeps/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertNotEqual(rc, 0)

    def test_ssh_into_dep(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/intohostname/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        runname = self._get_runname(outfile)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def test_reload(self):

        if 'CLOUDINITD_TESTENV' in os.environ:
            #this wont work in fake mode
            return

        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v", "-v", "-v", "boot",  "%s/reloadplan/badtop.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)
        self.assertNotEqual(rc, 0)

        rc = cloudinitd.cli.boot.main(["--name", runname, "reload",  "%s/reloadplan/goodtop.conf" % (self.plan_basedir)])
        self.assertEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["repair",  runname])
        self.assertEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["terminate",  runname])
        self.assertEqual(rc, 0)



    def test_validate_nolaunch(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)

        key = None
        secret = None
        url = None
        try:
            key = os.environ['CLOUDINITD_IAAS_ACCESS_KEY']
            secret = os.environ['CLOUDINITD_IAAS_SECRET_KEY']
            url = os.environ['CLOUDINITD_IAAS_URL']
        except:
            pass

        # XXX this test may fail for nimbus
        con = cloudinitd.cb_iaas.iaas_get_con(None, key=key, secret=secret, iaasurl=url)
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

    def bad_name_test(self):
        runname = str(uuid.uuid4()).split("-")[0]
        rc = cloudinitd.cli.boot.main(["status",  "%s" % (runname)])
        self.assertNotEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["terminate",  "%s" % (runname)])
        self.assertNotEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["reboot",  "%s" % (runname)])
        self.assertNotEqual(rc, 0)

    def bad_boot_args_test(self):
        rc = cloudinitd.cli.boot.main(["boot"])
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

    def simple_iceage_test(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/terminate/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        runname = self._get_runname(outfile)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "history", runname])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)

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

        if 'CLOUDINITD_TESTENV' in os.environ:
            bkfab = os.environ['CLOUDINITD_FAB']
            bkssh = os.environ['CLOUDINITD_SSH']
            os.environ['CLOUDINITD_FAB'] = "/bin/false"
            os.environ['CLOUDINITD_SSH'] = "/bin/false"

        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v","-v","-v","-v", "status", runname])
        if 'CLOUDINITD_TESTENV' in os.environ:
            os.environ['CLOUDINITD_FAB'] = bkfab
            os.environ['CLOUDINITD_SSH'] = bkssh
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
        iaas_url = svc.get_attr_from_bag('iaas_url')
        instance_id = svc.get_attr_from_bag('instance_id')
        con = iaas_get_con(None, key=key, secret=secret, iaasurl=iaas_url)
        instance = con.find_instance(instance_id)
        instance.terminate()

        if 'CLOUDINITD_TESTENV' in os.environ:
            bkfab = os.environ['CLOUDINITD_FAB']
            bkssh = os.environ['CLOUDINITD_SSH']
            os.environ['CLOUDINITD_FAB'] = "/bin/false"
            os.environ['CLOUDINITD_SSH'] = "/bin/false"

        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v","-v","-v","-v", "status", runname])
        if 'CLOUDINITD_TESTENV' in os.environ:
            os.environ['CLOUDINITD_FAB'] = bkfab
            os.environ['CLOUDINITD_SSH'] = bkssh
        self._dump_output(outfile)
        n = "ERROR"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        if 'CLOUDINITD_TESTENV' in os.environ:
            # in fake mode we cannot detect that an instance was killed
            self.assertEqual(rc, 0)
        else:
            self.assertNotEqual(rc, 0)

    def check_repair_error_test(self):
        if 'CLOUDINITD_TESTENV' in os.environ:
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
        url = svc.get_attr_from_bag('iaas_url')
        instance_id = svc.get_attr_from_bag('instance_id')
        con = iaas_get_con(svc._svc, key=key, secret=secret, iaasurl=url)
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

    def check_service_log_test(self):

        dir = os.path.expanduser("~/.cloudinitd/")
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "-v", "-l", "info", "boot",  "%s/oneservice/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()

        logfilename = dir + "/" + runname + "/sampleservice.log"
        self.assertTrue(os.path.exists(logfilename), "%s should exist" % (logfilename))
        os.path.getsize(logfilename)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)


    def test_outputwriter(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "-o", "/dev/null", "boot",  "%s/terminate/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)
        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "-o", "/dev/null", "status",  "%s" % (runname)])
        self.assertEqual(rc, 0)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def termfails_test(self):

        if 'CLOUDINITD_TESTENV' in os.environ:
            return
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "-o", "/dev/null", "boot",  "%s/termfail/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)

        n = "Starting up run"
        line = self._find_str(outfile, n)
        self.assertNotEqual(line, None)
        runname = line[len(n):].strip()
        print "run name is %s" % (runname)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        self._dump_output(outfile)
        line = self._find_str(outfile, "ERROR")
        self.assertNotEqual(line, None)


    def test_globals_success(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "--globalvar", "var1=world", "boot",  "%s/globals/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertEqual(rc, 0)

        runname = self._get_runname(outfile)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "--globalvar", "var1=world", "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)

    def test_globals_fail(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "boot",  "%s/globals/top.conf" % (self.plan_basedir)])
        self._dump_output(outfile)
        self.assertNotEqual(rc, 0)

        runname = self._get_runname(outfile)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "terminate",  "%s" % (runname)])
        line = self._find_str(outfile, "global variable var1 is not")
        self.assertNotEqual(line, None)

    def test_globals_file_success(self):
        (osf, outfile) = tempfile.mkstemp()
        os.close(osf)
        rc = cloudinitd.cli.boot.main(["-O", outfile, "--globalvarfile", "%s/globals/globals.ini" % (self.plan_basedir), "boot",  "%s/globals/top.conf" % (self.plan_basedir)])

        self._dump_output(outfile)
        self.assertEqual(rc, 0)

        runname = self._get_runname(outfile)

        rc = cloudinitd.cli.boot.main(["-O", outfile, "--globalvar", "var1=world", "terminate",  "%s" % (runname)])
        self.assertEqual(rc, 0)
