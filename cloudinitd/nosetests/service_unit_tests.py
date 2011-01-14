import uuid
from cloudinitd.cb_iaas import IaaSTestInstance
from cloudinitd.exceptions import APIUsageException
from cloudinitd.pollables import InstanceHostnamePollable
from cloudinitd.user_api import CloudInitD

__author__ = 'bresnaha'

import unittest

class ServiceUnitTests(unittest.TestCase):

    def test_baddir_name(self):
        try:
            cb = CloudInitD("baddir", db_name="badname")
            fail = True
        except APIUsageException, apiex:
            fail = False
        self.assertFalse(fail)

    def test_bad_opts1(self):
        try:
            cb = CloudInitD("/tmp")
            fail = True
        except APIUsageException, apiex:
            fail = False
        self.assertFalse(fail)

    def test_service_poll(self):
        h1 = str(uuid.uuid1())
        instance = IaaSTestInstance(h1, time_to_hostname=5)
        p = InstanceHostnamePollable(instance)
        p.start()
        rc = False
        while not rc:
            rc = p.poll()
        h2 = p.get_hostname()
        self.assertEquals(h1, h2)
        i = p.get_instance()
        self.assertEqual(instance, i)

if __name__ == '__main__':
    unittest.main()
