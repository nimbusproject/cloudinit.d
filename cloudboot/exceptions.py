__author__ = 'bresnaha'


class APIUsageException(Exception):

    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg

