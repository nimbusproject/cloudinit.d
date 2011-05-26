import cloudinitd
import cloudinitd.nosetests
from cloudinitd.user_api import CloudInitD
import tempfile
import logging



import time
import unittest
import os

class BanPlanTests(unittest.TestCase):

    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
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
        r_list = [i for i in i_list if i.get_state() == "running"]
        return r_list

    def test_badlevel_bootpgm(self):
        ilist_1 = self._get_running_vms()
        count1 = len(ilist_1)
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/badlevel2/top.conf"
        pass_ex = True
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        try:
            cb.start()
            cb.block_until_complete(poll_period=1.0)
        except Exception, ex:
            pass_ex = True
        self.assertTrue(pass_ex, "An exception should have happened and didn't")

        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)

        time.sleep(5)
        ilist_2 = self._get_running_vms()
        count2 = len(ilist_2)

        self.assertEqual(count1, count2, "the vm count before and after should be the same: %d %d" % (count1, count2))


    def test_badlevel_creds(self):
        ilist_1 = self._get_running_vms()
        count1 = len(ilist_1)
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/badlevel2.2/top.conf"

        pass_ex = True
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        try:
            cb.start()
            cb.block_until_complete(poll_period=1.0)
        except Exception, ex:
            pass_ex = True
        self.assertTrue(pass_ex, "An exception should have happened and didn't")

        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)

        time.sleep(5)
        ilist_2 = self._get_running_vms()
        count2 = len(ilist_2)

        self.assertEqual(count1, count2, "the vm count before and after should be the same: %d %d" % (count1, count2))


if __name__ == '__main__':
    unittest.main()
