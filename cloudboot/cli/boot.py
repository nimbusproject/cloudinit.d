#!/usr/bin/env python

import sys
import logging
from optparse import OptionParser
from cloudboot.cli.cmd_opts import bootOpts
from cloudboot.user_api import CloudBoot, CloudServiceException
from cloudboot.exceptions import MultilevelException
import cloudboot
import os
import cloudboot.cli.output

__author__ = 'bresnaha'

g_verbose = 1
g_action = ""

def print_chars(lvl, msg, color="default", bg_color="default", bold=False, underline=False):
    cloudboot.cli.output.write_output(lvl, g_verbose, msg, color=color, bg_color=bg_color, bold=bold, underline=underline)
    
# setup and validate options
def parse_commands(argv):
    global g_verbose

    u = """[options] <boot | status | terminate> <run name> [<top level launch plan> | <runame> | <clean>]
Boot and manage a launch plan
"""
    version = "cloudboot " + (cloudboot.Version)
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
    opt = bootOpts("loglevel", "l", "Controls how the level of detail in the log file.", "error", vals=["debug", "info", "warn", "error"])
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

    logger = logging.getLogger("cloudboot")
    logger.setLevel(loglevel)
    if options.logfile == None:
        options.logfile = "/dev/null"
    if options.logfile == "-":
        handler = logging.StreamHandler()
    else:
        handler = logging.handlers.RotatingFileHandler(
          options.logfile, maxBytes=102400, backupCount=5)

    logger.addHandler(handler)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
        
    options.logger = logger

    if not options.database:
        dbdir = os.path.expanduser("~/.cloudboot")
        if not os.path.exists(dbdir):
            os.mkdir(dbdir)
        options.database = dbdir

    if options.quiet:
        options.verbose = 0
    g_verbose = options.verbose

    return (args, options)

def level_callback(cb, action, current_level):
    global g_action

    if action == cloudboot.callback_action_started:
        print_chars(2, "Begin %s level %d...\n" % (g_action, current_level))
    elif action == cloudboot.callback_action_transition:
        #print_chars(1, ".")
        pass
    elif action == cloudboot.callback_action_complete:
        print_chars(1, "SUCCESS", color="green", bold=True)
        print_chars(1, " level %d\n" % (current_level))
    elif action == cloudboot.callback_action_error:
        print_chars(1, "Level %d ERROR.\n" % (current_level), color="red", bold=True)

def service_callback(cb, cloudservice, action, msg):
    global g_action
    
    if action == cloudboot.callback_action_started:
        print_chars(3, "\tStarted %s on service %s\n" % (g_action, cloudservice.name))
        sys.stdout.flush()
    elif action == cloudboot.callback_action_transition:             
        print_chars(5, "\t%s\n" % (msg))
    elif action == cloudboot.callback_action_complete:
        print_chars(2, "\tSUCCESS", color="green")
        print_chars(2, " service %s %s\n" % (cloudservice.name, g_action))
        print_chars(4, "\t\thostname: %s\n" % (cloudservice.get_attr_from_bag("hostname")))
        print_chars(4, "\t\tinstance: %s\n" % (cloudservice.get_attr_from_bag("instance_id")))

    elif action == cloudboot.callback_action_error:
        print_chars(1, "\tService %s ERROR\n" % (cloudservice.name), color="red", bold=True)
        print_chars(1, "%s\n" % (msg))


def launch_new(options, config_file):

    cb = CloudBoot(options.database, db_name=options.name, config_file=config_file, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=False, boot=True, ready=True)
    print_chars(1, "Starting up run %s\n" % (cb.run_name))
    cb.start()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex

    return (0, cb.run_name)

def status(options, dbname):

    cb = CloudBoot(options.database, db_name=dbname, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=False, boot=False, ready=True, continue_on_error=True)
    print_chars(1, "Checking status on %s\n" % (cb.run_name))
    cb.start()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex

    return 0

def terminate(options, dbname):
    cb = CloudBoot(options.database, db_name=dbname, level_callback=level_callback, service_callback=service_callback, log=options.logger, terminate=True, boot=False, ready=False, continue_on_error=True)
    print_chars(1, "Terminating %s\n" % (cb.run_name))
    cb.shutdown()
    try:
        cb.block_until_complete(poll_period=0.1)
    except CloudServiceException, svcex:
        print svcex
    except MultilevelException, mex:
        print mex

def clean(options, dbname):
    try:
        print_chars(1, "Attempting to terminate %s\n" % (dbname))
        terminate(options, dbname)
    except Exception, ex:
        print_chars(1, "Termination for %s failed: %s" % (dbname, str(ex)))
    path = "%s/cloudboot-%s.db" % (options.database, dbname)
    print_chars(1, "deleting the db file %s\n" % (path))
    if not os.path.exists(path):
        raise Exception("That DB does not seem to exist: %s" % (path))
    os.remove(path)
    return 0

def list(options):
    l = os.listdir(options.database)

    for db in l:
        if db.find("cloudboot-") == 0:
            name = db.replace("cloudboot-", "")
            print_chars(0, name[:-3] + "\n")

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
            (rc, name) = launch_new(options, args[1])
        elif command == "status":
            rc = status(options, args[1])
        elif command == "terminate":
            rc = terminate(options, args[1])
        elif command == "clean":
            rc = clean(options, args[1])
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
    return rc


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
