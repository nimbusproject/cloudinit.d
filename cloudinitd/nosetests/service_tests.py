import cloudinitd
from cloudinitd.exceptions import ServiceException, APIUsageException
import cloudinitd.nosetests
from cloudinitd.user_api import CloudInitD
import tempfile
import logging



import unittest
import os

class ServiceTests(unittest.TestCase):

    def setUp(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir

    def tearDown(self):
        cloudinitd.close_log_handlers()

    def dep_not_found_test(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/oneservice/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        ok = False
        try:
            cb.find_dep("notaservice", "whatever")
        except APIUsageException, ex:
            ok = True
        self.assertTrue(ok, "Test should have thrown an exception")
        cb.block_until_complete(poll_period=1.0)

        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)
        fname = cb.get_db_file()
        os.remove(fname)

    def get_status_test(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/oneservice/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)

        svc = cb.get_service("sampleservice")
        status = svc.get_iaas_status()
        self.assertEqual("running", status, "status is %s" % (status))

        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)
        fname = cb.get_db_file()
        os.remove(fname)

    def dep_keys_test(self):
        self.plan_basedir = cloudinitd.nosetests.g_plans_dir
        dir = tempfile.mkdtemp()
        conf_file = self.plan_basedir + "/oneservice/top.conf"
        cb = CloudInitD(dir, conf_file, terminate=False, boot=True, ready=True)
        cb.start()
        cb.block_until_complete(poll_period=1.0)

        svc = cb.get_service("sampleservice")
        attr_keys = svc.get_keys_from_bag()
        # until we figure out how to get __dict__ values from the sqlalchemy objects this will be in complete
        expectations = [
            "hostname",
            "instance_id",
#            "name",
#            "level_id",
#            "image",
#            "iaas",
#            "allocation",
#            "keyname",
#            "localkey",
#            "username",
#            "scp_username",
#            "readypgm",
#            "hostname",
#            "bootconf",
#            "bootpgm",
#            "instance_id",
#            "iaas_url",
#            "iaas_key",
#            "iaas_secret",
#            "contextualized",
#            "securitygroups",
            "webmessage"
            ]
        for e in expectations:
            self.assertTrue(e in attr_keys, "The key %s should exist in %s" % (e, str(attr_keys)))

        cb = CloudInitD(dir, db_name=cb.run_name, terminate=True, boot=False, ready=False)
        cb.shutdown()
        cb.block_until_complete(poll_period=1.0)
        fname = cb.get_db_file()
        os.remove(fname)


if __name__ == '__main__':
    unittest.main()
