import traceback
import sys
import os



class CloudInitDException(Exception):
    def __init__(self, ex):
        self._base_ex = ex
        exc_type, exc_value, exc_traceback = sys.exc_info()
        self._base_stack = traceback.format_tb(exc_traceback)

    def __str__(self):
        return str(self._base_ex)

    def get_stack(self):
        return str(self._base_stack)

class APIUsageException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class TimeoutException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class IaaSException(CloudInitDException):
    def __init__(self, msg):
        CloudInitDException.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return str(self.msg)

class ConfigException(Exception):
    def __init__(self, msg, ex=None):
        Exception.__init__(self, msg)
        self._source_ex = ex


class PollableException(CloudInitDException):
    def __init__(self, p, ex):
        CloudInitDException.__init__(self, ex)
        self.pollable = p

    def __str__(self):
        return CloudInitDException.__str__(self)

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
        try:
            s = s + os.linesep + "stdout : %s" % (str(self.stdout))
            s = s + os.linesep + "stderr : %s" % (str(self.stderr))
            s = s + os.linesep + str(self._base_ex)
        except Exception, ex:
            s = str(s)
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
        PollableException.__str__(self)
        s = "["
        d = ""
        for ex in self.exception_list:
            s = s + d + str(ex) + ":" + str(type(ex))
            d = ","
        s = s + "]"
        return s


