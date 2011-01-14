#!/usr/bin/env python

import sys
import logging
from optparse import OptionParser
import stat
from cloudinitd.cli.cmd_opts import bootOpts
from cloudinitd.user_api import CloudInitD, CloudServiceException
from cloudinitd.exceptions import MultilevelException
import cloudinitd
import os
import cloudinitd.cli.output
from optparse import SUPPRESS_HELP

__author__ = 'bresnaha'

g_verbose = 1
g_action = ""
g_repair = False
g_outfile = None

def print_chars(lvl, msg, color="default", bg_color="default", bold=False, underline=False, inverse=False):
    global g_outfile
    if g_outfile:
        g_outfile.write(msg)
    cloudinitd.cli.output.write_output(lvl, g_verbose, msg, color=color, bg_color=bg_color, bold=bold, underline=underline, inverse=inverse)
    
# setup and validate options
def parse_commands(argv):
    global g_verbose

    u = """[options] <boot | status | terminate> <run name> [<top level launch plan> | <run name> | <clean>]
Boot and manage a launch plan"""
    version = "cloudinitd " + (cloudinitd.Version)
    parser = OptionParser(usage=u, version=version)

    opt = bootOpts("verbose", "v", "Print more output", 1, count=True)
    opt.add_opt(parser)
    opt = bootOpts("quiet", "q", "Print no output", False, flag=True)
    opt.add_opt(parser)
    opt = bootOpts("name", "n", "Set the run name, only relevant for boot (by default the system picks)", None)
    opt.add_opt(parser)
    opt = bootOpts("database", "d", "Path to the db directory", None)
    opt.add_opt(parser)
    opt = bootOpts("logfile", "f", "Path to logfile", None)
    opt.add_opt(parser)
    opt = bootOpts("loglevel", "l", "Controls the level of detail in the log file", "error", vals=["debug", "info", "warn", "error"])
    opt.add_opt(parser)
    opt = bootOpts("repair", "r", "Restart all failed services, only relevant for the status command", False, flag=True)
    opt.add_opt(parser)
    opt = bootOpts("noclean", "c", "Do not delete the database, only relevant for the terminate command", False, flag=True)
    opt.add_opt(parser)
    opt = bootOpts("outstream", "O", SUPPRESS_HELP, None)
    opt.add_opt(parser)

    (options, args) = parser.parse_args(args=argv)
    
    if options.loglevel == "debug":
        loglevel = logging.DEBUG
    elif options.loglevel == "info":
        loglevel = logging.INFO
    elif options.loglevel == "warn":
        loglevel = logging.WARN
    elif options.loglevel == "error":
        loglevel = logging.ERROR

    logger = logging.getLogger("cloudinitd")
    logger.setLevel(loglevel)
    if options.logfile == None:
        options.logfile = "/dev/null"
    if options.logfile == "-":
        handler = logging.StreamHandler()
    else:
        handler = logging.handlers.RotatingFileHandler(
          options.logfile, maxBytes=100*1024*1024, backupCount=5)

    logger.addHandler(handler)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
        
    options.logger = logger

    if not options.database:
        dbdir = os.path.expanduser("~/.cloudinitd")
        if not os.path.exists(dbdir):
            os.mkdir(dbdir)
        os.chmod(dbdir, stat.S_IWUSR | stat.S_IXUSR | stat.S_IRUSR)
        options.database = dbdir

    if options.quiet:
        options.verbose = 0
    g_verbose = options.verbose

    if options.outstream:
        global g_outfile
        g_outfile = open(options.outstream, "w")

    return (args, options)

def level_callback(cb, action, current_level):
    global g_action

    if action == cloudinitd.callback_action_started:
        print_chars(2, "Begin %s level %d...\n" % (g_action, current_level))
    elif action == cloudinitd.callback_action_transition:
        #print_chars(1, ".")
        pass
    elif action == cloudinitd.callback_action_complete:
        print_chars(1, "SUCCESS", color="green", bold=True)
        print_chars(1, " level %d\n" % (current_level))
    elif action == cloudinitd.callback_action_error:
        print_chars(1, "Level %d ERROR.\n" % (current_level), color="red", bold=True)

def service_callback(cb, cloudservice, action, msg):
    global g_action
    
    if action == cloudinitd.callback_action_started:
        print_chars(3, "\tStarted %s on service %s\n" % (g_action, cloudservice.name))
        sys.stdout.flush()
    elif action == cloudinitd.callback_action_transition:
        print_chars(5, "\t%s\n" % (msg))
    elif action == cloudinitd.callback_action_complete:
        print_chars(2, "\tSUCCESS", color="green")
        print_chars(2, " service %s %s\n" % (cloudservice.name, g_action))
        print_chars(4, "\t\thostname: %s\n" % (cloudservice.get_attr_from_bag("hostname")))
        print_chars(4, "\t\tinstance: %s\n" % (cloudservice.get_attr_from_bag("instance_id")))

    elif action == cloudinitd.callback_action_error:
        print_chars(1, "\tService %s ERROR\n" % (cloudservice.name), color="red", bold=True)
        print_chars(1, "%s\n" % (msg))
        global g_repair
        if g_repair:
            return cloudinitd.callback_return_restart
    return cloudinitd.callback_return_default


def launch_new(options, config_file):

    cb = CloudInitD(options.database, db_name=options.name, config_file=config_file, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=False, boot=True, ready=True)
    print_chars(1, "Starting up run ")
    print_chars(1, "%s\n" % (cb.run_name), inverse=True, color="green", bold=True)
    cb.start()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex
    except KeyboardInterrupt:
        print_chars(1, "Canceling (this will not clean up already launched services)...")
        cb.cancel()

    return (0, cb.run_name)

def status(options, dbname):
    global g_repair

    g_repair = options.repair

    cb = CloudInitD(options.database, db_name=dbname, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=False, boot=False, ready=True, continue_on_error=True)
    print_chars(1, "Checking status on %s\n" % (cb.run_name))
    cb.start()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex
    except KeyboardInterrupt:
        print_chars(1, "Canceling...")
        cb.cancel()

    return 0

def terminate(options, dbname):
    cb = CloudInitD(options.database, db_name=dbname, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=True, boot=False, ready=False, continue_on_error=True)
    print_chars(1, "Terminating %s\n" % (cb.run_name))
    cb.shutdown()
    try:
        cb.block_until_complete(poll_period=0.1)
        if not options.noclean:
            path = "%s/cloudinitd-%s.db" % (options.database, dbname)
            print_chars(1, "deleting the db file %s\n" % (path))
            if not os.path.exists(path):
                raise Exception("That DB does not seem to exist: %s" % (path))
            os.remove(path)

        return 0
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex
    except KeyboardInterrupt:
        print_chars(1, "Canceling...")
        cb.cancel()
    return 1

def reboot(options, dbname):
    cb = CloudInitD(options.database, db_name=dbname, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=True, boot=False, ready=False, continue_on_error=True)
    print_chars(1, "Rebooting %s\n" % (cb.run_name))
    cb.shutdown()
    try:
        print_chars(1, "Terminating all services %s\n" % (cb.run_name))
        cb.block_until_complete(poll_period=0.1)
        cb = CloudInitD(options.database, db_name=dbname, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=False, boot=True, ready=True, continue_on_error=False)
        print_chars(1, "Booting all services %s\n" % (cb.run_name))
        cb.start()
        cb.block_until_complete(poll_period=0.1)
        return 0
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex
    except KeyboardInterrupt:
        print_chars(1, "Canceling...")
        cb.cancel()
    return 1

def list(options):
    l = os.listdir(options.database)

    for db in l:
        if db.find("cloudinitd-") == 0:
            name = db.replace("cloudinitd-", "")
            print_chars(0, name[:-3] + "\n")
    return 0

def main(argv=sys.argv[1:]):
    # first process options
    if len(argv) == 0:
        argv.append("--help")
    (args, options) = parse_commands(argv)

    # process the command
    global g_action
    command = args[0]
    g_action = command
    try:
        if command == "boot":
            if len(args) < 2:
                print "The boot command requires a top level file.  See --help"
                return 1
            (rc, name) = launch_new(options, args[1])
        elif command == "status":
            if len(args) < 2:
                print "The %s command requires a run name.  See --help" % (command)
                return 1
            rc = status(options, args[1])
        elif command == "terminate":
            if len(args) < 2:
                print "The %s command requires a run name.  See --help" % (command)
                return 1
            rc = terminate(options, args[1])
        elif command == "reboot":
            if len(args) < 2:
                print "The %s command requires a run name.  See --help" % (command)
                return 1
            rc = reboot(options, args[1])
        elif command == "list":
            rc = list(options)
        else:
            print "Invalid command.  Run with --help"
            rc = 1
        print ""
    except SystemExit:
        raise
    except Exception, ex:
        print_chars(0, str(ex))
        print_chars(0, "\n")
        if options.verbose > 1:
            raise
        rc = 1
    finally:
        if g_outfile:
            g_outfile.close()
    return rc


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
