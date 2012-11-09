import os
from cloudinitd.exceptions import ConfigException, CloudInitDException, APIUsageException, IaaSException, IaaSException, MultilevelException, ServiceException



import uuid
import unittest
import cloudinitd
import logging
import traceback

class FakeSvc(object):
    def __init__(self, n):
        self.name = n

class BasicUnitTests(unittest.TestCase):

    def tearDown(self):
        cloudinitd.close_log_handlers()

    def test_logging(self):
        cloudinitd.log(logging, logging.DEBUG, "testmessage")
        cloudinitd.log(None, logging.DEBUG, "testmessage")
        try:
            raise Exception("TESTER")
        except:
            cloudinitd.log(logging, logging.DEBUG, "test stack", traceback)

    def test_get_env(self):
        env_key = str(uuid.uuid1())
        val = str(uuid.uuid1())
        x = cloudinitd.get_env_val("env." + env_key)
        self.assertEqual(x, None)
        os.environ[env_key] = val
        x = cloudinitd.get_env_val("env." + env_key)
        self.assertEqual(x, val)

    def test_exceptions(self):
        cbex = CloudInitDException(Exception("test"))
        print cbex
        msg = "bad usage"
        ex = APIUsageException(msg)
        self.assertEqual(msg, str(ex))
        ex = IaaSException(Exception("test"))
        print ex
        ex = MultilevelException([ex], [ex], 5)
        print ex
        fakesvc = FakeSvc("name")
        ex = ServiceException(Exception("tester"), fakesvc, msg="msg")
        print ex
        ex = ConfigException("msg")
        ex = IaaSException(ex)


if __name__ == '__main__':
    unittest.main()
