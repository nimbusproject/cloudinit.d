from cloudinitd.exceptions import *
from cloudinitd.user_api import *
from cloudinitd.statics import *
import urlparse

service_state_initial = 0
service_state_launched = 2
service_state_contextualized = 4
service_state_terminated = 6

g_open_loggers = []

Version = "1.0RC2"

def find_true():
    cmds = [
              "true",
              "/bin/true",
              "echo hello"
           ]
    for c in cmds:
        try:
            rc = os.system(c)
            if rc == 0:
                return c
        except:
            pass

    raise Exception("There is no way to set true on your system.")

def log(logger, level, msg, tb=None):

    msg = msg.decode("utf8")
    if logger is None:
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

    logfile = None
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

    global g_open_loggers
    g_open_loggers.append(handler)

    return (logger, logfile)

def close_log_handlers():
    global g_open_loggers
    for l in g_open_loggers:
        l.close()


def parse_url(url):
    ndx = url.find("://")
    if ndx < 0:
        url = "https://" + url
    url_parts = urlparse.urlparse(url)

    path = url_parts.path
    if not path:
        path = "/"

    return (url_parts.scheme, url_parts.hostname, url_parts.port, path)
