__author__ = 'bresnaha'


class APIUsageException(Exception):
    def __init__(self):
        Exception.__init__(self)

class TimeoutException(Exception):
    def __init__(self):
        Exception.__init__(self)

class IaaSException(Exception):
    def __init__(self):
        Exception.__init__(self)

class ConfigException(Exception):
    def __init__(self):
        Exception.__init__(self)

class PollableException(Exception):
    def __init__(self, p, ex):
        Exception.__init__(self, ex)
        self.pollable = p

class ServiceException(PollableException):
    def __init__(self, ex, svc):
        Exception.__init__(self, ex)
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


