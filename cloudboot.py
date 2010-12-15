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
        sys.stdout.write("Booting level %d...\n" % (current_level))
        sys.stdout.flush()
    elif action == cloudboot.callback_action_transition:
        pass
    elif action == cloudboot.callback_action_complete:
        sys.stdout.write("Level %d complete.\n" % (current_level))
        sys.stdout.flush()
    elif action == cloudboot.callback_action_error:
        sys.stdout.write("Level %d complete with error.\n" % (current_level))

def service_callback(cb, cloudservice, action, msg):
    if action == cloudboot.callback_action_started:
        print "\tService %s started" % (cloudservice.name)
    elif action == cloudboot.callback_action_transition:
        print "\t%s : %s" %(cloudservice.name, msg)        
    elif action == cloudboot.callback_action_complete:
        print "\tService %s OK" % (cloudservice.name)
    elif action == cloudboot.callback_action_error:
        print "Service %s error: %s" % (cloudservice.name, str(cloudservice.get_error()))

def launch_new(args, options):
    logger = logging.getLogger("simple_example")
    logger.setLevel(logging.WARN)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARN)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    cb = CloudBoot("/home/bresnaha/Dev/", config_file=args[1], level_callback=level_callback, service_callback=service_callback, log=logger)
    print "Starting up run %s" % (cb.run_name)
    cb.start()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print ex

    except MultilevelException, mex:
        print mex

    return 0

def status(args):
    pass

def terminate(args):
    cb = CloudBoot("/home/bresnaha/Dev/", db_name=args[1])
    print "Terminating run %s" %(args[1])

    for i in range(1, cb.get_level_count()+1):
        ndx = cb.get_level_count() - i
        cs_list = cb.get_level(ndx)


def main(argv=sys.argv[1:]):
    # first process options
    (args, options) = parse_commands(argv)
    # process the command
    command = args[0]
    if command == "boot":
        rc = launch_new(args, options)
    elif command == "status":
        rc = status(args, options)
    elif command == "terminate":
        rc = terminate(args, options)
    else:
        print "Invalid command.  Run with --help"
        rc = 1
    print ""

    return rc


if __name__ == "__main__":
    rc = main()
    print "PAU"
    sys.exit(rc)
