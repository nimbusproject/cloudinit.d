import sys
import os

__author__ = 'bresnaha'

from cloudinitd.exceptions import *
from cloudinitd.user_api import *
from cloudinitd.statics import *

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


def make_logger(log_level, runname, logdir=None, servicename=None):

    if log_level == "debug":
        loglevel = logging.DEBUG
    elif log_level == "info":
        loglevel = logging.INFO
    elif log_level == "warn":
        loglevel = logging.WARN
    elif log_level == "error":
        loglevel = logging.ERROR

    logname = "cloudinitd-" + runname
    if servicename:
        logname = logname + "-" + servicename

    logger = logging.getLogger(logname)
    logger.setLevel(loglevel)

    if logdir == "-":
        handler = logging.StreamHandler()
    else:
        if not logdir:
            logdir = os.path.expanduser("~/.cloudinitd")

        if not os.path.exists(logdir):
            try:
                os.mkdir(logdir)
            except OSError:
                pass

        if servicename:
            logdir = logdir + "/%s" % (runname)
            if not os.path.exists(logdir):
                try:
                    os.mkdir(logdir)
                except OSError:
                    pass
            logfile = logdir + "/" + servicename + ".log"
        else:
            logfile = logdir + "/" + runname + ".log"
            
        handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=100*1024*1024, backupCount=5)

    logger.addHandler(handler)

    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if loglevel == logging.DEBUG:
        fmt = fmt + " || at source line %(filename)s : %(lineno)s"

    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)

    return logger
