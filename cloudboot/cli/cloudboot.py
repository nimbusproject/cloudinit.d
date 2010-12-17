import sys
import logging
from optparse import OptionParser
from cloudboot.cli.cmd_opts import bootOpts
from cloudboot.user_api import CloudBoot, CloudServiceException
from cloudboot.exceptions import MultilevelException
import cloudboot
import os

__author__ = 'bresnaha'
Version = "0.1"


# setup and validate options
def parse_commands(argv):
    u = """[options] <launch | status | terminate> <run name> [<top level launch plan> | <runame>]
Boot and manage a launch plan
"""
    version = "%prog " + (Version)
    parser = OptionParser(usage=u, version=version)

    opt = bootOpts("database", "d", "Path to the db directory", None)
    opt.add_opt(parser)
    opt = bootOpts("logfile", "f", "Path to logfile", None)
    opt.add_opt(parser)
    opt = bootOpts("loglevel", "l", "Controls how the level of detail in the log file.", "error", vals=["debug", "info", "warn", "error"])
    opt.add_opt(parser)

    (options, args) = parser.parse_args(args=argv)

    if options.loglevel == "debug":
        loglevel = logging.DEBUG
    elif options.loglevel == "info":
        loglevel = logging.INFO
    elif options.loglevel == "warn":
        loglevel = logginf.WARN
    elif options.loglevel == "error":
        loglevel = logging.ERROR

    logger = logging.getLogger("cloudboot")
    logger.setLevel(loglevel)
    if options.logfile != None:
        handler = logging.handlers.RotatingFileHandler(
              options.logfile, maxBytes=102400, backupCount=5)
    else:
        handler = logging.StreamHandler()

    logger.addHandler(handler)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    options.logger = logger

    if not options.database:
        dbdir = os.path.expanduser("~/.cloudboot")
        if not os.path.exists(dbdir):
            os.mkdir(dbdir)
        options.database = dbdir

    return (args, options)

def level_callback(cb, action, current_level):
    if action == cloudboot.callback_action_started:
        sys.stdout.write("\nBooting level %d...\n" % (current_level))
        sys.stdout.flush()
    elif action == cloudboot.callback_action_transition:
        pass
    elif action == cloudboot.callback_action_complete:
        sys.stdout.write("\nLevel %d complete.\n" % (current_level))
        sys.stdout.flush()
    elif action == cloudboot.callback_action_error:
        sys.stdout.write("Level %d complete with error.\n" % (current_level))

def service_callback(cb, cloudservice, action, msg):
    if action == cloudboot.callback_action_started:
        sys.stdout.write("\n\tService %s started" % (cloudservice.name))
        sys.stdout.flush()
    elif action == cloudboot.callback_action_transition:             
        sys.stdout.write(".")
        sys.stdout.flush()
    elif action == cloudboot.callback_action_complete:
        sys.stdout.write("\n\tService %s OK" % (cloudservice.name))
        sys.stdout.flush()
    elif action == cloudboot.callback_action_error:
        print "Service %s error: %s" % (cloudservice.name, str(cloudservice.get_error()))

def launch_new(options, config_file):

    cb = CloudBoot(options.database, config_file=config_file, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=False, boot=True, ready=True)
    print "Starting up run %s" % (cb.run_name)
    cb.start()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex

    return (0, cb.run_name)

def status(options, dbname):

    cb = CloudBoot(options.database, db_name=dbname, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=False, boot=False, ready=True)
    print "Checking status on %s" % (cb.run_name)
    cb.start()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex

    return 0

def terminate(options, dbname):
    cb = CloudBoot(options.database, db_name=dbname, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=True, boot=False, ready=False)
    print "Terminating %s" % (cb.run_name)
    cb.shutdown()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex

def test_up_and_down(options, config_file):
    (rc, name) = launch_new(options, config_file)
    if rc != 0:
        return 1
    args[1] = name
    rc = status(options, config_file)
    if rc != 0:
        return 1
    rc = terminate(options, config_file)
    return rc

def main(argv=sys.argv[1:]):
    # first process options
    (args, options) = parse_commands(argv)

    # process the command
    command = args[0]
    if command == "boot":
        (rc, name) = launch_new(options, args[1])
    elif command == "status":
        rc = status(options, args[1])
    elif command == "terminate":
        rc = terminate(options, args[1])
    elif command == "test":
        rc = test_up_and_down(options, args[1])
    else:
        print "Invalid command.  Run with --help"
        rc = 1
    print ""

    return rc


if __name__ == "__main__":
    rc = main()
    print "PAU"
    sys.exit(rc)
