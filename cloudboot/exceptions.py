import traceback
import sys
import os

__author__ = 'bresnaha'

class CloudBootException(Exception):
    def __init__(self, ex):
        self._base_ex = ex
        exc_type, exc_value, exc_traceback = sys.exc_info()
        self._base_stack = traceback.format_tb(exc_traceback)

    def __str__(self):
        return repr(self._base_stack)


class APIUsageException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class TimeoutException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class IaaSException(CloudBootException):
    def __init__(self, ex):
        CloudBootException.__init__(self, ex)

class ConfigException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class PollableException(CloudBootException):
    def __init__(self, p, ex):
        CloudBootException.__init__(self, ex)
        self.pollable = p

class ServiceException(PollableException):
    def __init__(self, ex, svc, msg=None, stdout="", stderr=""):
        PollableException.__init__(self, svc, ex)
        self._svc = svc
        self.stdout = stdout
        self.stderr = stderr
        self.msg = msg

    def __str__(self):
        s = "Error while processing the service: %s" % (self._svc.name)
        if self.msg:
            s = s + os.linesep + self.msg
        s = s + os.linesep + "stdout : %s" % (self.stdout)
        s = s + os.linesep + "stderr : %s" % (self.stderr)
        return s

class ProcessException(PollableException):
    def __init__(self, pollable, ex, stdout, stderr, rc=None):
        PollableException.__init__(self, pollable, ex)
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = rc

class MultilevelException(PollableException):
    def __init__(self, exs, pollables, level):
        PollableException.__init__(self, pollables[0], exs[0])
        self.level = level
        self.exception_list = exs
        self.pollable_list = pollables

    def __str__(self):
        s = "["
        d = ""
        for ex in self.exception_list:
            s = s + d + str(ex)
            d = ","
        s = s + "]"
        return s


