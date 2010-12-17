import sys
import os

__author__ = 'bresnaha'

from cloudboot.exceptions import *
from cloudboot.user_api import *
from cloudboot.statics import *

Version = "0.1"

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

def get_env_val(key):
    if key.find("env.") == 0:
        env_key = key[4:]
        try:
            key = os.environ[env_key]
        except:
            key = None
    return key

