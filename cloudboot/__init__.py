import sys

__author__ = 'bresnaha'

from cloudboot.exceptions import *
from cloudboot.user_api import *
from cloudboot.statics import *

def log(logger, level, msg, tb=None):

    if logger == None:
        print msg
        return

    logger.log(level, msg)

    if tb != None:
        logger.log(level, "Stack trace")
        logger.log(level, "===========")
        stack = tb.format_exc()
        logger.log(level, stack)
        logger.log(level, "===========")
        logger.log(level, sys.exc_info()[0])
