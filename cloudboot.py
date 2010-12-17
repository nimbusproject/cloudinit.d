import sys
import logging
from optparse import OptionParser
from cmd_opts import bootOpts
from cloudboot.pollables import MultiLevelPollable
from cloudboot.user_api import CloudBoot, CloudServiceException
from cloudboot.exceptions import ServiceException, MultilevelException
import cloudboot

__author__ = 'bresnaha'
Version = "0.1"

g_log = logging

def parse_commands(argv):
    u = """[options] <launch | status | terminate> <run name> <top level launch plan>
Boot and manage a launch plan
"""
    version = "%prog " + (Version)
    parser = OptionParser(usage=u, version=version)

    opt = bootOpts("database", "d", "Path to the db directory", None)
    opt.add_opt(parser)
    opt = bootOpts("logfile", "f", "Path to logfile", None)
    opt.add_opt(parser)
    opt = bootOpts("access", "a", "IaaS access ID", None)
    opt.add_opt(parser)
    opt = bootOpts("secret", "s", "IaaS access secret", None)
    opt.add_opt(parser)

    (options, args) = parser.parse_args(args=argv)
    
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
        sys.stdout.write("%s\n" % (msg))
        sys.stdout.flush()
    elif action == cloudboot.callback_action_complete:
        sys.stdout.write("\n\tService %s OK" % (cloudservice.name))
        sys.stdout.flush()
    elif action == cloudboot.callback_action_error:
        print "Service %s error: %s" % (cloudservice.name, str(cloudservice.get_error()))

def launch_new(args, options, logger=None):

    cb = CloudBoot("/home/bresnaha/Dev/", config_file=args[1], level_callback=level_callback, service_callback=service_callback, log=logger, terminate=False, boot=True, ready=True)
    print "Starting up run %s" % (cb.run_name)
    cb.start()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex

    return (0, cb.run_name)

def status(args, options, logger=None):

    cb = CloudBoot("/home/bresnaha/Dev/", db_name=args[1], level_callback=level_callback, service_callback=service_callback, log=logger, terminate=False, boot=False, ready=True)
    print "Checking status on %s" % (cb.run_name)
    cb.start()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex

    return 0

def terminate(args, options, logger=None):
    cb = CloudBoot("/home/bresnaha/Dev/", db_name=args[1], level_callback=level_callback, service_callback=service_callback, log=logger, terminate=True, boot=False, ready=False)
    print "Terminating %s" % (cb.run_name)
    cb.shutdown()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex

def test_up_and_down(args, options, logger=None):
    (rc, name) = launch_new(args, options, logger)
    if rc != 0:
        return 1
    args[1] = name
    rc = status(args, options, logger)
    if rc != 0:
        return 1
    rc = terminate(args, options, logger)
    return rc

def main(argv=sys.argv[1:]):
    # first process options
    (args, options) = parse_commands(argv)

    logger = logging.getLogger("simple_example")
    logger.setLevel(logging.WARN)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARN)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # process the command
    command = args[0]
    if command == "boot":
        (rc, name) = launch_new(args, options, logger)
    elif command == "status":
        rc = status(args, options, logger)
    elif command == "terminate":
        rc = terminate(args, options, logger)
    elif command == "test":
        rc = test_up_and_down(args, options, logger)
    else:
        print "Invalid command.  Run with --help"
        rc = 1
    print ""

    return rc


if __name__ == "__main__":
    rc = main()
    print "PAU"
    sys.exit(rc)
