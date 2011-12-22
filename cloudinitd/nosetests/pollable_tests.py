import unittest
import uuid
import cloudinitd
from cloudinitd.pollables import *




class PollableTests(unittest.TestCase):

    def tearDown(self):
        cloudinitd.close_log_handlers()

    def test_popen_fail(self):
        cmd = "/bin/false"
        pexe = PopenExecutablePollable(cmd, allowed_errors=0)
        pexe.start()
        try:
            failed = True
            rc = pexe.poll()
            while not rc:
                rc = pexe.poll()
        except ProcessException, pex:
            failed = False
        self.assertFalse(failed)

    def test_popen_fail_retry(self):
        cmd = "/bin/false"
        pexe = PopenExecutablePollable(cmd, allowed_errors=3)
        pexe.start()
        try:
            failed = True
            rc = pexe.poll()
            while not rc:
                rc = pexe.poll()
        except ProcessException, pex:
            failed = False
            ex = pexe.get_exception()
            self.assertEqual(ex, pex)
        self.assertFalse(failed)

    def test_null_poll(self):
        np = NullPollable()
        np.start()
        rc = np.poll()
        self.assertTrue(rc)

    def test_popen_true(self):
        cmd = cloudinitd.find_true()
        pexe = PopenExecutablePollable(cmd, allowed_errors=0)
        pexe.start()
        rc = pexe.poll()
        while not rc:
            rc = pexe.poll()

    def test_popen_output(self):
        test_out = str(uuid.uuid1())
        cmd = "/bin/echo %s" % (test_out)
        pexe = PopenExecutablePollable(cmd, allowed_errors=0)
        pexe.start()

        rc = pexe.poll()
        while not rc:
            rc = pexe.poll()
        out = pexe.get_output().strip()
        print test_out
        print out
        self.assertEqual(test_out, out)

    def test_popen_badcmd(self):
        cmd = str(uuid.uuid1())
        pexe = PopenExecutablePollable(cmd, allowed_errors=0)
        pexe.start()
        try:
            failed = True
            rc = pexe.poll()
            while not rc:
                rc = pexe.poll()
        except ProcessException, pex:
            failed = False
        self.assertFalse(failed)

    def test_popen_timeoutex(self):
        cmd = "/bin/sleep 30"
        pexe = PopenExecutablePollable(cmd, allowed_errors=0, timeout=5)
        pexe.start()
        try:
            failed = True
            rc = pexe.poll()
            while not rc:
                rc = pexe.poll()
        except TimeoutException, pex:
            failed = False
        self.assertFalse(failed)

    def test_multilevel_simple(self):
        cmd = cloudinitd.find_true()
        pexe1_1 = PopenExecutablePollable(cmd, allowed_errors=0)
        pexe1_2 = PopenExecutablePollable(cmd, allowed_errors=0)
        pexe2_1 = PopenExecutablePollable(cmd, allowed_errors=0)
        pexe2_2 = PopenExecutablePollable(cmd, allowed_errors=0)

        mcp = MultiLevelPollable()
        mcp.add_level([pexe1_1, pexe1_2])
        mcp.add_level([pexe2_1, pexe2_2])

        mcp.start()

        rc = False
        while not rc:
            rc = mcp.poll()

    def test_multilevel_error(self):
        cmd = cloudinitd.find_true()
        pexe1_1 = PopenExecutablePollable(cmd, allowed_errors=0, timeout=60)
        pexe1_2 = PopenExecutablePollable(cmd, allowed_errors=0, timeout=60)
        pexe2_1 = PopenExecutablePollable(cmd, allowed_errors=0, timeout=60)
        pexe2_2 = PopenExecutablePollable("NotACommand", allowed_errors=0, timeout=5)

        mcp = MultiLevelPollable()
        mcp.add_level([pexe1_1, pexe1_2])
        mcp.add_level([pexe2_1, pexe2_2])
        mcp.start()

        rc = False
        try:
            failed = True
            while not rc:
                rc = mcp.poll()
        except:
            failed = False
        self.assertFalse(failed)


    def test_popen_cancel(self):
        cmd = "/bin/sleep 100000"
        pexe1_1 = PopenExecutablePollable(cmd, allowed_errors=0)

        pexe1_1.start()
        pexe1_1.cancel()
        rc = False
        try:
            while not rc:
                rc = pexe1_1.poll()
            self.fail("Should have raised an exception")
        except ProcessException, pex:
            pass
