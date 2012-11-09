from unittest.case import SkipTest
import uuid
import cloudinitd
import cloudinitd.nosetests
from cloudinitd.statics import REMOTE_WORKING_DIR_ENV_STR
from cloudinitd.user_api import CloudInitD
import tempfile
import unittest
import os

class RemoteDirInspectionTests(unittest.TestCase):

    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        self.remote_dir = "/tmp/" + str(uuid.uuid4()).split("-")[0]
        os.environ[REMOTE_WORKING_DIR_ENV_STR] = self.remote_dir

    def tearDown(self):
        del os.environ[REMOTE_WORKING_DIR_ENV_STR]
        cloudinitd.close_log_handlers()

    def _get_running_vms(self):

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
        return i_list

    def test_env_set(self):
        if cloudinitd.nosetests.is_a_test():
            raise SkipTest()
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/oneservice/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)
        svc = cb.get_service("sampleservice")
        ssh_cmd = svc.get_ssh_command() + " ls -l %s" % (self.remote_dir)

        # form test directory command
        print ssh_cmd

        rc = os.system(ssh_cmd)
        self.assertEquals(rc, 0)

        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)


if __name__ == '__main__':
    unittest.main()
