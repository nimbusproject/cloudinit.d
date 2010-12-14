import traceback

__author__ = 'bresnaha'

class CloudBootException(Exception):
    def __init__(self, ex):
        self._base_ex = ex
        self._base_stack = traceback.format_tb()

    def __str__(self):
        return str(self._base_stack)


class APIUsageException(Exception):
    def __init__(self):
        Exception.__init__(self)

class TimeoutException(Exception):
    def __init__(self):
        Exception.__init__(self)

class IaaSException(CloudBootException):
    def __init__(self, ex):
        CloudBootException.__init__(self, ex)

class ConfigException(Exception):
    def __init__(self):
        Exception.__init__(self)

class PollableException(CloudBootException):
    def __init__(self, p, ex):
        CloudBootException.__init__(self, ex)
        self.pollable = p

class ServiceException(PollableException):
    def __init__(self, ex, svc):
        PollableException.__init__(self, ex)
        self._svc = svc

class ProcessException(PollableException):
    def __init__(self, pollable, ex, stdout, stderr):
        PollableException.__init__(self, pollable, ex)
        self.stdout = stdout
        self.stderr = stderr

class MultilevelException(PollableException):
    def __init__(self, exs, pollables, level):
        PollableException.__init__(self, pollables[0], exs[0])
        self.level = level
        self.exception_list = exs
        self.pollable_list = pollables

    def __str__(self):
        return str(self.exception_list)


