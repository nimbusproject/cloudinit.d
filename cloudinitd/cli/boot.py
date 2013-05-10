
from datetime import datetime

import sys
from optparse import OptionParser
import uuid
import stat
import logging
from cloudinitd.cli.cmd_opts import bootOpts
from cloudinitd.global_deps import set_global_var, set_global_var_file, global_merge_down
from cloudinitd.user_api import CloudInitD, CloudServiceException
from cloudinitd.exceptions import MultilevelException, APIUsageException, ConfigException
import cloudinitd
import os
import cloudinitd.cli.output
from optparse import SUPPRESS_HELP
import simplejson as json



g_verbose = 1
g_action = ""
g_repair = False
g_outfile = None
g_commands = {}
g_options = None # just a lame way to thread info to callbacks.

def _return_key_val(var_str):
    l_a = var_str.split("=", 1)
    if len(l_a) != 2:
        raise Exception("Invalid global variable string.  It must be in the format <key>=<value>")
    return l_a

def _deal_with_cmd_line_globals(options):
    if options.globalvar:
        for var_str in options.globalvar:
            (key, value) = _return_key_val(var_str)
            set_global_var(key, value, 3)

    if options.globalvarfile:
        for filename in options.globalvarfile:
            set_global_var_file(filename, 2)

    # if we add this to the conf file that will go on rank 1
    global_merge_down()


def print_chars(lvl, msg, color="default", bg_color="default", bold=False, underline=False, inverse=False):
    global g_outfile
    if g_outfile:
        g_outfile.write(msg)
    cloudinitd.cli.output.write_output(lvl, g_verbose, msg, color=color, bg_color=bg_color, bold=bold, underline=underline, inverse=inverse)

# setup and validate options
def parse_commands(argv):
    global g_verbose

    u = """[options] <command> [<top level launch plan> | <run name>]
Boot and manage a launch plan
Run with the command 'commands' to see a list of all possible commands
"""
    version = "cloudinitd " + (cloudinitd.Version)
    parser = OptionParser(usage=u, version=version)

    all_opts = []
    opt = bootOpts("verbose", "v", "Print more output", 1, count=True)
    all_opts.append(opt)
    opt.add_opt(parser)
    opt = bootOpts("validate", "x", "Check that boot plan is valid before launching it.", False, flag=True)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("dryrun", "y", "Perform dry run on the boot plan.  The IaaS service is never contacted but all other actions are performed.  This option offers an addition level of plan validation of -x.", False, flag=True)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("quiet", "q", "Print no output", False, flag=True)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("name", "n", "Set the run name, only relevant for boot and reload (by default the system picks)", None)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("database", "d", "Path to the db directory", None)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("logdir", "f", "Path to the base log directory.", None)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("loglevel", "l", "Controls the level of detail in the log file", "info", vals=["debug", "info", "warn", "error"])
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("logstack", "s", "Log stack trace information (extreme debug level)", False, flag=True)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("noclean", "c", "Do not delete the database, only relevant for the terminate command", False, flag=True)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("safeclean", "C", "Do not delete the database on failed terminate, only relevant for the terminate command", False, flag=True)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("kill", "k", "This option only applies to the iceage command.  When on it will terminate all VMs started with IaaS associated with this run to date.  This should be considered an extreme measure to prevent IaaS resource leaks.", False, flag=True)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("outstream", "O", SUPPRESS_HELP, None)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("remotedebug", "X", SUPPRESS_HELP, False, flag=True)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("output", "o", "Create an json document which describes the application and write it to the associated file.  Relevant for boot and status", None)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("globalvar", "g", "Add a variable to global variable space", None, append_list=True)
    opt.add_opt(parser)
    all_opts.append(opt)
    opt = bootOpts("globalvarfile", "G", "Add a file to global variable space", None, append_list=True)
    opt.add_opt(parser)
    all_opts.append(opt)


    homedir = os.path.expanduser("~/.cloudinitd")
    try:
        if not os.path.exists(homedir):
            os.mkdir(homedir)
            os.chmod(homedir, stat.S_IWUSR | stat.S_IXUSR | stat.S_IRUSR)
    except Exception, ex:
        print_chars(0, "Error creating cloudinit.d directort %s : %s" % (homedir, str(ex)))

    (options, args) = parser.parse_args(args=argv)

    _deal_with_cmd_line_globals(options)

    for opt in all_opts:
        opt.validate(options)

    if not options.name:
        options.name = str(uuid.uuid4()).split("-")[0]

    if options.logdir is None:
        options.logdir = os.path.expanduser("~/.cloudinitd/")

    (options.logger, logfile) = cloudinitd.make_logger(options.loglevel, options.name, logdir=options.logdir)
    if not options.database:
        dbdir = os.path.expanduser("~/.cloudinitd")
        options.database = dbdir

    if options.logstack:
        logger = logging.getLogger("stacktracelog")
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        logdir = os.path.join(options.logdir, options.name)
        if not os.path.exists(logdir):
            try:
                os.mkdir(logdir)
            except OSError:
                pass
        stacklogfile = os.path.join(logdir, "stacktrace.log")
        handler = logging.handlers.RotatingFileHandler(stacklogfile, maxBytes=100*1024*1024, backupCount=5)
        logger.addHandler(handler)
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(fmt)
        handler.setFormatter(formatter)


    if options.quiet:
        options.verbose = 0
    g_verbose = options.verbose

    if options.outstream:
        global g_outfile
        g_outfile = open(options.outstream, "w")
    else:
        g_outfile = None

    if options.remotedebug:
        try:
            from pydev import pydevd
            debug_cs = os.environ['CLOUDINITD_DEBUG_CS'].split(':')
            debug_host = debug_cs[0]
            debug_port = int(debug_cs[1])
            pydevd.settrace(debug_host, port=debug_port, stdoutToServer=True, stderrToServer=True)
        except ImportError, e:
            print_chars(0, "Could not import remote debugging library: %s\n" % str(e), color="red", bold=True)
        except KeyError:
            print_chars(0, "If you want to do remote debugging please set the env CLOUDINITD_DEBUG_CS to the contact string of you expected debugger.\n", color="red", bold=True)
        except:
            print_chars(0, "Please verify the format of your contact string to be <hostname>:<port>.\n", color="red", bold=True)

    global g_options
    g_options = options
    return (args, options)

def friendly_timedelta(td):
    if td is None:
        s = None
    else:
        s = (td.microseconds + (td.seconds + td.days * 24 * 3600) * float(10**6)) / float(10**6)
    if s < 0:
        s = 0
    return "%.1fs" % s

def level_callback(cb, action, current_level):
    global g_action

    if action == cloudinitd.callback_action_started:
        print_chars(2, "Begin %s level %d...\n" % (g_action, current_level))
    elif action == cloudinitd.callback_action_transition:
        #print_chars(1, ".")
        pass
    elif action == cloudinitd.callback_action_complete:
        runtime_str = friendly_timedelta(cb.get_level_runtime(current_level))
        print_chars(1, "SUCCESS", color="green", bold=True)
        print_chars(1, " level %d" % (current_level))
        print_chars(4, " (%s)" % runtime_str)
        print_chars(1, "\n")

    elif action == cloudinitd.callback_action_error:
        print_chars(1, "Level %d ERROR.\n" % (current_level), color="red", bold=True)

def service_callback(cb, cloudservice, action, msg):
    global g_action

    if action == cloudinitd.callback_action_started:
        print_chars(3, "\t%s\n" % (msg))

        global g_options
        print_chars(3, "\tlogging to %s%s/%s.log\n" % (g_options.logdir, g_options.name, cloudservice.name))
        sys.stdout.flush()
    elif action == cloudinitd.callback_action_transition:
        print_chars(5, "\t%s\n" % (msg))
    elif action == cloudinitd.callback_action_complete:

        runtime_str = friendly_timedelta(cloudservice.get_runtime())
        print_chars(2, "\tSUCCESS", color="green")
        print_chars(2, " service %s %s" % (cloudservice.name, g_action))
        print_chars(2, " (%s)\n" % runtime_str)
        print_chars(4, "\t\thostname: %s\n" % (cloudservice.get_attr_from_bag("hostname")))
        print_chars(4, "\t\tinstance: %s\n" % (cloudservice.get_attr_from_bag("instance_id")))

    elif action == cloudinitd.callback_action_error:
        print_chars(1, "\tService %s ERROR\n" % (cloudservice.name), color="red", bold=True)
        print_chars(1, "%s\n" % (msg))
        global g_repair
        if g_repair:
            return cloudinitd.callback_return_restart
    return cloudinitd.callback_return_default

def reload_conf(options, args):
    """
    Reload an updated launch plan configuration into the database of the run name supplied with --name.  This is typically followed by a repair of the same run name.
    """
    if len(args) < 2:
        print "The reload command requires a top level file.  See --help"
        return 1

    config_file = args[1]
    print_chars(1, "Loading the launch plan for run ")
    print_chars(1, "%s\n" % (options.name), inverse=True, color="green", bold=True)
    cb = CloudInitD(options.database, log_level=options.loglevel, db_name=options.name, config_file=config_file, level_callback=level_callback, service_callback=service_callback, logdir=options.logdir, fail_if_db_present=False, terminate=False, boot=False, ready=False)
    if options.validate:
        print_chars(1, "Validating the launch plan.\n")
        errors = cb.boot_validate()
        if len(errors) > 0:
            print_chars(0, "The boot plan is not valid.\n", color = "red")
            for (svc, ex) in errors:
                print_chars(1, "Service %s had the error:\n" % (svc.name))
                print_chars(1, "\t%s" %(str(ex)))
            return 1
    return 0


def _getenv_or_none(k):
    try:
        return os.environ[k]
    except KeyError:
        return None

def _setenv_or_none(k, v):
    if v is None:
        os.unsetenv(k)
    else:
        os.environ[k] = v

def _write_json_doc(options, cb):
    if options.output:
        json_doc = cb.get_json_doc()
        doc_str = json.dumps(json_doc, indent=4)
        f = open(options.output, "w")
        f.write(doc_str)
        f.close()


def launch_new(options, args):
    """
    Boot a new launch plan.  You must supply the path to a top level configuration file.  A run name will be displayed in the output.  See --help for more information.
    """

    if len(args) < 2:
        print "The boot command requires a top level file.  See --help"
        return 1

    config_file = args[1]
    print_chars(1, "Starting up run ")
    print_chars(1, "%s\n" % (options.name), inverse=True, color="green", bold=True)

    cb = CloudInitD(options.database, log_level=options.loglevel, db_name=options.name, config_file=config_file, level_callback=level_callback, service_callback=service_callback, logdir=options.logdir, terminate=False, boot=True, ready=True, fail_if_db_present=True)
    print_chars(3, "Logging to: %s%s.log\n"  % (options.logdir, options.name))

    if options.validate:
        print_chars(1, "Validating the launch plan.\n")
        errors = cb.boot_validate()
        if len(errors) > 0:
            print_chars(0, "The boot plan is not valid.\n", color = "red")
            for (svc, ex) in errors:
                print_chars(1, "Service %s had the error:\n" % (svc.name))
                print_chars(1, "\t%s" %(str(ex)))
            return 1

    if options.dryrun:
        test_env = _getenv_or_none('CLOUDINITD_TESTENV')
        host_time_env = _getenv_or_none('CLOUDINITD_CBIAAS_TEST_HOSTNAME_TIME')
        fab_env = _getenv_or_none('CLOUDINITD_FAB')
        ssh_env = _getenv_or_none('CLOUDINITD_SSH')

        print_chars(1, "Performing a dry run...\n", bold=True)
        os.environ['CLOUDINITD_TESTENV'] = "2"
        os.environ['CLOUDINITD_CBIAAS_TEST_HOSTNAME_TIME'] = "0.0"
        os.environ['CLOUDINITD_FAB'] = cloudinitd.find_true()
        os.environ['CLOUDINITD_SSH'] = cloudinitd.find_true()

        try:
            (rc, cb) = _launch_new(options, args, cb)
            print_chars(1, "Dry run successful\n", bold=True, color="green")
        finally:
            _setenv_or_none('CLOUDINITD_TESTENV', test_env)
            _setenv_or_none('CLOUDINITD_CBIAAS_TEST_HOSTNAME_TIME', host_time_env)
            _setenv_or_none('CLOUDINITD_FAB', fab_env)
            _setenv_or_none('CLOUDINITD_SSH', ssh_env)
            if not options.noclean:
                path = "%s/cloudinitd-%s.db" % (options.database, cb.run_name)
                if not os.path.exists(path):
                    raise Exception("That DB does not seem to exist: %s" % (path))
                os.remove(path)

        return rc

    (rc, cb) = _launch_new(options, args, cb)
    return rc


def _launch_new(options, args, cb):
    cb.pre_start_iaas()

    print_chars(1, "Starting the launch plan.\n")
    cb.start()
    try:
        try:
            cb.block_until_complete(poll_period=0.1)
        except CloudServiceException, svcex:
            print svcex
            return (1, cb)
        except MultilevelException, mex:
            print mex
            return (1, cb)
        except KeyboardInterrupt:
            print_chars(1, "Canceling (this will not clean up already launched services)...")
            cb.cancel()
    finally:
        fake_args = ["clean", options.name]
        clean_ice(options, fake_args)

    rc = 0
    ex = cb.get_exception()
    if ex is None:
        ex_list = cb.get_all_exceptions()
        if ex_list:
            ex = ex_list[-1]
    if ex:
        print_chars(4, "An error occured %s" % (str(ex)))
        rc = 1

    _write_json_doc(options, cb)

    return (rc, cb)

def status(options, args):
    """
    Check on the status of an already booted plan.  You must supply the run name of the booted plan.
    """
    if len(args) < 2:
        print "The status command requires a run name.  See --help"
        return 1
    rc = _status(options, args)
    return rc

def _status(options, args):
    global g_repair

    dbname = args[1]
    c_on_e = not g_repair
    options.name = dbname

    cb = CloudInitD(options.database, db_name=dbname, log_level=options.loglevel, level_callback=level_callback, service_callback=service_callback, logdir=options.logdir, terminate=False, boot=False, ready=True, continue_on_error=c_on_e)
    print_chars(1, "Checking status on %s\n" % (cb.run_name))
    cb.start()
    try:
        try:
            cb.block_until_complete(poll_period=0.1)
        except CloudServiceException, svcex:
            print svcex
            return 1
        except MultilevelException, mex:
            print mex
            return 1
        except KeyboardInterrupt:
            print_chars(1, "Canceling...")
            cb.cancel()
    finally:
        fake_args = ["clean", dbname]
        clean_ice(options, fake_args)

    rc = 0
    if g_repair:
        ex = cb.get_last_exception()
    else:
        ex = cb.get_exception()
        if ex is None:
            ex_list = cb.get_all_exceptions()
            if ex_list:
                ex = ex_list[-1]
    if ex:
        print_chars(4, "An error occured %s" % (str(ex)))
        rc = 1

    _write_json_doc(options, cb)

    return rc

def terminate(options, args):
    """
    Terminate an already booted plan.  You must supply the run name of the booted plan.
    """
    if len(args) < 2:
        print "The terminate command requires a run name.  See --help"
        return 1

    for dbname in args[1:]:
        options.name = dbname
        rc = 0
        try:
            cb = CloudInitD(options.database, log_level=options.loglevel, db_name=dbname, level_callback=level_callback, service_callback=service_callback, logdir=options.logdir, terminate=True, boot=False, ready=False, continue_on_error=True)
            print_chars(1, "Terminating %s\n" % (cb.run_name))
            cb.shutdown()

            cb.block_until_complete(poll_period=0.1)
            if not options.noclean:
                path = "%s/cloudinitd-%s.db" % (options.database, dbname)
                if not os.path.exists(path):
                    raise Exception("That DB does not seem to exist: %s" % (path))
                if not options.safeclean or (cb.get_exception() is None and not cb.get_all_exceptions()):
                    print_chars(1, "Deleting the db file %s\n" % (path))
                    os.remove(path)
                else:
                    print_chars(4, "There were errors when terminating %s, keeping db\n" % (cb.run_name))

            ex = cb.get_exception()
            if ex is None:
                ex_list = cb.get_all_exceptions()
                if ex_list:
                    ex = ex_list[-1]
            if ex is not None:
                print_chars(4, "An error occured %s" % (str(ex)))
                raise ex
        except CloudServiceException, svcex:
            print svcex
            rc = 1
        except Exception, mex:
            rc = 1
        except KeyboardInterrupt:
            print_chars(1, "Canceling...")
            cb.cancel()
            return 1

    return rc

def reboot(options, args):
    """
    Reboot an already booted plan.  You must supply the run name of the booted plan.
    """
    if len(args) < 2:
        print "The reboot command requires a run name.  See --help"
        return 1
    dbname = args[1]
    cb = CloudInitD(options.database, db_name=dbname, log_level=options.loglevel, level_callback=level_callback, service_callback=service_callback, logdir=options.logdir, terminate=True, boot=False, ready=False, continue_on_error=True)
    print_chars(1, "Rebooting %s\n" % (cb.run_name))
    cb.shutdown()
    try:
        try:
            print_chars(1, "Terminating all services %s\n" % (cb.run_name))
            options.logger.info("Terminating all services")
            cb.block_until_complete(poll_period=0.1)
            options.logger.info("Starting services back up")
            cb = CloudInitD(options.database, db_name=dbname, log_level=options.loglevel, level_callback=level_callback, service_callback=service_callback, logdir=options.logdir, terminate=False, boot=True, ready=True, continue_on_error=False)
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
    finally:
        fake_args = ["clean", dbname]
        clean_ice(options, fake_args)
    return 1

def list_commands(options, args):
    """
    List all of the possible commands accepted by this program.
    """
    line_len = 60
    global g_commands
    for cmd in g_commands:
        func = g_commands[cmd]
        if not func.__doc__:
            continue
        print_chars(1, "%s: " % (cmd), bold=True)
        msg = "\n\t" + func.__doc__.strip()
        ndx = line_len
        while ndx < len(msg):
            i = msg[ndx:].find(" ")
            if i < 0:
                break
            i = i + ndx
            msg = msg[:i] + "\n\t" + msg[i+1:]
            ndx = ndx + line_len
        print_chars(1, "%s\n" % (msg))
    return 0

def list(options, args):
    """
    List all existing booted plans.
    """
    l = os.listdir(options.database)

    for db in l:
        if db.find("cloudinitd-") == 0 and db[-3:] == ".db":
            name = db.replace("cloudinitd-", "")
            print_chars(0, name[:-3] + "\n")
    return 0


def iceage(options, args):
    if len(args) < 2:
        print "The iceage command requires a run name.  See --help"
        return 1
    dbname = args[1]

    cb = CloudInitD(options.database, db_name=dbname, log_level=options.loglevel, logdir=options.logdir, terminate=False, boot=False, ready=True)
    ha = cb.get_iaas_history()

    print_chars(0, "ID      \t:\tstate:\tassociated service\n")
    for h in ha:
        print_chars(1, "%s\t:\t%s\t:\t" % (h.get_id(), h.get_service_name()))
        state = h.get_state()
        clean = False
        color = None
        if state == "running":
            color = "green"
            clean = True
        elif state == "terminated" or state == "shutting-down":
            color="red"
        elif state == "pending":
            color="yellow"
            clean = True

        print_chars(1, ": %s\n" % (state), color=color)
        if options.kill and clean:
            print_chars(1, "Terminating %s\n" % (h.get_id()), bold=True)
            h.terminate()

    return 0



def clean_ice(options, args):
    """
    Clean all orphaned VMs
    """
    if len(args) < 2:
        print "The iceage command requires a run name.  See --help"
        return 1
    dbname = args[1]

    cb = CloudInitD(options.database, db_name=dbname, log_level=options.loglevel, logdir=options.logdir, terminate=False, boot=False, ready=True)
    ha = cb.get_iaas_history()

    for h in ha:
        state = h.get_state()
        handle = h.get_service_iaas_handle()
        if state == "running":
            if handle != h.get_id():
                print_chars(2, "Terminating an orphaned VM %s\n" % (h.get_id()), bold=True)
                h.terminate()
            elif h.get_context_state() == cloudinitd.service_state_initial:
                print_chars(2, "Terminating pre-staged VM %s\n" % (h.get_id()), bold=True)
                h.terminate()

    return 0


def repair(options, args):
    """
    Check the status of all services.  If any services fail, reboot them.
    """
    global g_repair
    g_repair = True
    if len(args) < 2:
        print "The repair command requires a run name.  See --help"
        return 1
    return _status(options, args)


def main(argv=sys.argv[1:]):
    # first process options
    if not argv:
        argv = []
    if len(argv) == 0:
        argv.append("--help")
    try:
        (args, options) = parse_commands(argv)
    except SystemExit:
        return 0
    if not args or len(args) == 0:
        print "You must provide a command.  Run with --help"
        return 1

    # process the command
    global g_action
    global g_outfile

    command = args[0]
    g_action = command

    g_commands["boot"] = launch_new
    g_commands["status"] = status
    g_commands["terminate"] = terminate
    g_commands["reboot"] = reboot
    g_commands["list"] = list
    g_commands["commands"] = list_commands
    g_commands["repair"] = repair
    g_commands["reload"] = reload_conf
    g_commands["history"] = iceage
    g_commands["clean"] = clean_ice

    if command not in g_commands:
        print "Invalid command.  Run with --help"
        return 1

    func = g_commands[command]
    try:
        try:
            rc = func(options, args)
        except SystemExit:
            raise
        except APIUsageException, apiex:
            print_chars(0, str(apiex))
            print_chars(0, "\n")
            print_chars(0, "see ")
            print_chars(0, "%s" % (options.logdir), inverse=True, color="red")
            print_chars(0,  " for more details\n")
            options.logger.error("An internal usage error occurred.  Most likely due to an update to the services db without the use of the cloudinitd program: %s", str(apiex))
            rc = 1
        except ConfigException, cex:
            print_chars(0, str(cex))
            print_chars(0, "\n")
            print_chars(0, "see ")
            print_chars(0, "%s" % (options.logdir), inverse=True, color="red")
            print_chars(0,  " for more details\n")
            print_chars(0,  "Check your launch plan and associated environment variables for the above listed errors.\n")
            options.logger.error("A configuration error occured.  Please check your launch plan and its associated environment variables")
            rc = 1
        except Exception, ex:
            print_chars(0, str(ex))
            print_chars(0, "\n")
            print_chars(0, "see ")
            print_chars(0, "%s" % (options.logdir), inverse=True, color="red")
            print_chars(0,  " for more details\n")
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
