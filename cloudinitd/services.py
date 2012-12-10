
import pipes
import shlex
import traceback
import urllib
import re
import tempfile
import string

import simplejson as json

import cb_iaas
from cloudinitd.global_deps import get_global
from cloudinitd.persistence import BagAttrsObject, IaaSHistoryObject
from cloudinitd.pollables import MultiLevelPollable, InstanceHostnamePollable, PopenExecutablePollable, InstanceTerminatePollable, PortPollable, Pollable
import bootfabtasks
from cloudinitd.exceptions import APIUsageException, ConfigException, ServiceException, MultilevelException
from cloudinitd.statics import *
from cloudinitd.cb_iaas import *


class BootTopLevel(object):
    """
    This class is the top level boot description. It holds the parent Multilevel boot object which contains a set
    of many pollables.  The object also contains a way to get variable information from every service created.
    A service cannot be created without this object.  This object holds a dictionary of all services which is
    used for querying dependencies
    """

    def __init__(self, level_callback=None, service_callback=None, log=logging, boot=True, ready=True, terminate=False, continue_on_error=False):
        self.services = {}
        self._log = log
        self._multi_top = MultiLevelPollable(log=log, callback=level_callback, continue_on_error=continue_on_error)
        self._continue_on_error = continue_on_error
        self._service_callback = service_callback
        self._boot = boot
        self._ready = ready
        self._terminate = terminate

    @cloudinitd.LogEntryDecorator
    def reverse_order(self):
        self._multi_top.reverse_order()

    @cloudinitd.LogEntryDecorator
    def add_level(self, lvl_list):
        self._multi_top.add_level(lvl_list)

    @cloudinitd.LogEntryDecorator
    def get_current_level(self):
        return self._multi_top.get_level()

    @cloudinitd.LogEntryDecorator
    def start(self):
        self._multi_top.start()

    @cloudinitd.LogEntryDecorator
    def get_services(self, basename=None):
        if not basename:
            return self.services.items()

        svcs = []
        for (k, v) in self.services:
            ndx = k.find(basename)
            if ndx == 0:
                svcs.append(v)

        return svcs

    @cloudinitd.LogEntryDecorator
    def get_service(self, name):
        return self.services[name]

    @cloudinitd.LogEntryDecorator
    def cancel(self):
        self._multi_top.cancel()

    @cloudinitd.LogEntryDecorator
    def poll(self):
        return self._multi_top.poll()

    @cloudinitd.LogEntryDecorator
    def new_service(self, s, db, boot=None, ready=None, terminate=None, log=None, logfile=None, run_name=None):

        if s.name in self.services.keys():
            raise APIUsageException("A service by the name of %s is already know to this boot configuration.  Please check your config files and try another name" % (s.name))

        if s.image is None and s.hostname is None:
            raise APIUsageException("You must have an image or a hostname or there will be no VM")

        if boot is None:
            boot = self._boot
        if ready is None:
            ready = self._ready
        if terminate is None:
            terminate = self._terminate
        if not log:
            log = self._log
        self._logfile = logfile

        # logname = <log dir>/<runname>/s.name
        svc = SVCContainer(db, s, self, log=log, callback=self._service_callback, boot=boot, ready=ready, terminate=terminate, logfile=self._logfile, run_name=run_name)
        self.services[s.name] = svc
        return svc

    @cloudinitd.LogEntryDecorator
    def find_dep(self, svc_name, attr):
        try:
            svc = self.services[svc_name]
        except KeyError:
            raise APIUsageException("service %s not found" % (svc_name))
        return svc.get_dep(attr)

    @cloudinitd.LogEntryDecorator
    def get_exception(self):
        return self._multi_top._exception

    @cloudinitd.LogEntryDecorator
    def get_json_doc(self):
        doc = {}
        count = 0
        levels = []
        for level in self._multi_top.levels:
            count = count + 1
            lvl_doc = {}
            lvl_doc['level'] = count
            svc_list = []
            for s in level:
                s_doc = s.generate_attr_doc()
                svc_list.append(s_doc)
            lvl_doc['services'] = svc_list
            levels.append(lvl_doc)
        doc['levels'] = levels
        return doc

    def get_level_runtime(self, level_ndx):
        times = self._multi_top.get_level_times()
        if level_ndx >= len(times):
            return None
        return times[level_ndx]

    def get_runtime(self):
        return self._multi_top.get_runtime()


class SVCContainer(Pollable):
    """
    This object represents a service which is the leaf object in the boot tree.  This service is a special case pollable type
    that consists of up to 3 other pollable types  a level pollable is used to keep the other MultiLevelPollable moving in order
    """

    def __init__(self, db, s, top_level, boot=True, ready=True, terminate=False, log=logging, callback=None, reload=False, logfile=None, run_name=None):
        Pollable.__init__(self)

        self._log = log
        self._attr_bag = {}
        self._myname = s.name

        # we need to separate out pollables.  bootconf and ready cannot be run until the instances has a hostname
        # terminate will be run first (for restarts only)
        # first pollable set is terminate, then hostname.  next is bootconf, then ready
        self._readypgm = s.readypgm
        self._s = s
        self.name = s.name
        self.run_name = run_name
        self._db = db
        self._top_level = top_level
        self._logfile = logfile

        # if we are reloading we need to examine the current state to see where things let off
        if reload:
            #
            if self._s.state == 0:
                pass

        self._stagedir = "%s/%s" % (get_remote_working_dir(), self.name)
        self._validate_and_reinit(boot=boot, ready=ready, terminate=terminate, callback=callback, repair=reload)

        self._db.db_commit()
        self._restart_limit = 2
        self._restart_count = 0

    @cloudinitd.LogEntryDecorator
    def _clean_up(self):
        cloudinitd.log(self._log, logging.DEBUG, "Cleanup")
        self._term_host_pollers = None
        self._pollables = None
        self._ssh_poller = None
        self._ssh_poller2 = None
        self._ready_poller = None
        self._boot_poller = None
        self._terminate_poller = None
        self._rmdir_poller = None
        self._shutdown_poller = None
        self.last_exception = None
        self.exception_list = []
        self._port_poller = None

    @cloudinitd.LogEntryDecorator
    def _validate_and_reinit(self, boot=True, ready=True, terminate=False, callback=None, repair=False):
        if boot and self._s.state == cloudinitd.service_state_contextualized and not terminate:
            raise APIUsageException("trying to boot an already contextualized service and not terminating %s %s %s" % (str(boot), str(self._s.state), str(terminate)))

        #if self._s.contextualized == 0 and not boot and not terminate and repair:
        #    cloudinitd.log(self._log, logging.WARN, "%s was asked not to boot but it has not yet been booted.  We are automatically changing this to boot.  We are also turning on terminate in case an iaas handle is associate with this" % (self.name))
        #    boot = True
        #    terminate = True

        self._do_boot = boot
        self._do_ready = ready
        self._do_terminate = terminate
        self._hostname_poller = None
        self._term_host_pollers = None
        self._pollables = None
        self._callback = callback
        self._running = False
        self._ssh_poller = None
        self._ssh_poller2 = None
        self._ready_poller = None
        self._boot_poller = None
        self._terminate_poller = None
        self._shutdown_poller = None
        self._rmdir_poller = None
        self.last_exception = None
        self.exception_list = []

        self._boot_output_file = None
        self._port_poller = None

        self._ssh_port = 22

        self._iass_started = False
        self._make_first_pollers()

    @cloudinitd.LogEntryDecorator
    def _teminate_done(self, poller):
        cloudinitd.log(self._log, logging.DEBUG, "%s hit terminate done callback" % (self.name))

        self._s.state = cloudinitd.service_state_terminated
        if self._s.image:
            self._s.hostname = None
#        self._s.instance_id = None
        self._db.db_commit()
        cloudinitd.log(self._log, logging.DEBUG, "%s terminate done callback completed" % (self.name))

    @cloudinitd.LogEntryDecorator
    def get_iaas_status(self):
        if not self._hostname_poller:
            return None
        return self._hostname_poller.get_status()

    @cloudinitd.LogEntryDecorator
    def _make_first_pollers(self):

        self._term_host_pollers = MultiLevelPollable(log=self._log)
        if self._do_terminate:
            if self._s.state == cloudinitd.service_state_terminated:
                cloudinitd.log(self._log, logging.WARN, "%s has already been terminated." % (self.name))
            else:
                if self._s.terminatepgm:
                    self._do_attr_bag()
                    cmd = self._get_termpgm_cmd()
                    cloudinitd.log(self._log, logging.INFO, "%s adding the terminate program to the poller %s" % (self.name, cmd))
                    self._terminate_poller = PopenExecutablePollable(cmd, log=self._log, allowed_errors=1, callback=self._context_cb, timeout=self._s.pgm_timeout)
                    self._term_host_pollers.add_level([self._terminate_poller])
                    pass
                else:
                    cloudinitd.log(self._log, logging.DEBUG, "%s no terminate program specified, right to terminate" % (self.name))

                cmd = self._get_directory_cleanup_cmd()
                self._rmdir_poller = PopenExecutablePollable(cmd, log=self._log, allowed_errors=1, timeout=self._s.pgm_timeout)
                self._term_host_pollers.add_level([self._rmdir_poller])
                if self._s.instance_id:
                    iaas_con = iaas_get_con(self)
                    try:
                        instance = iaas_con.find_instance(self._s.instance_id)
                        self._shutdown_poller = InstanceTerminatePollable(instance, log=self._log, done_cb=self._teminate_done)
                        self._term_host_pollers.add_level([self._shutdown_poller])
                    except IaaSException, iaas_ex:
                        emsg = "Skipping terminate due to IaaS exception %s" % (str(iaas_ex))
                        self._execute_callback(cloudinitd.callback_action_transition, emsg)
                        cloudinitd.log(self._log, logging.INFO, emsg)
                else:
                    cloudinitd.log(self._log, logging.DEBUG, "%s no instance id for termination" % (self.name))
                    self._teminate_done(None)
        else:
            cloudinitd.log(self._log, logging.DEBUG, "%s skipping the terminate program" % (self.name))

        if not self._do_boot:
            cloudinitd.log(self._log, logging.INFO, "%s not doing boot, returning early" % (self.name))
            return

        if self._s.image:
            cloudinitd.log(self._log, logging.INFO, "%s launching IaaS %s" % (self.name, self._s.image))
            self._hostname_poller = InstanceHostnamePollable(svc=self, log=self._log, timeout=self._s.pgm_timeout, done_cb=self._hostname_poller_done)
            self._term_host_pollers.add_level([self._hostname_poller])
        else:
            cloudinitd.log(self._log, logging.INFO, "%s no IaaS image to launch" % (self.name))

    @cloudinitd.LogEntryDecorator
    def pre_start_iaas(self):
        (rc, emsg) = cb_iaas.iaas_validate(self, self._log)
        if rc != 0:
            msg = "A warning has issued regarding your plan.  Please check the log file: %s" % (emsg)
            self._execute_callback(cloudinitd.callback_action_transition, msg)

        self._term_host_pollers.pre_start()

        if self._hostname_poller:
            self._s.instance_id = self._hostname_poller.get_instance_id()
            self._execute_callback(cloudinitd.callback_action_transition, "Have instance id %s for %s" % (self._s.instance_id, self.name))
            self._s.state = cloudinitd.service_state_launched
            self._db.db_commit()

        self._iass_started = True
        if self._do_boot:
            self._execute_callback(cloudinitd.callback_action_started, "Started IaaS work for %s" % (self.name))

    @cloudinitd.LogEntryDecorator
    def _make_pollers(self):
        if self._do_boot or self._do_ready:
            self._do_attr_bag()

        self._ready_poller = None
        self._boot_poller = None
        self._terminate_poller = None
        self._rmdir_poller = None

        self._pollables = MultiLevelPollable(log=self._log)

        if self._s.state == cloudinitd.service_state_contextualized:
            allowed_es_ssh = 1
        elif self._s.local_exe:
            allowed_es_ssh = 1
        else:
            allowed_es_ssh = 128

        if (self._do_boot or self._do_ready) and not self._s.local_exe:
            cloudinitd.log(self._log, logging.DEBUG, "Adding the port poller to %s " % (self._s.hostname))
            self._port_poller = PortPollable(self._expand_attr(self._s.hostname), self._ssh_port, retry_count=allowed_es_ssh, log=self._log, timeout=self._s.pgm_timeout)
            self._pollables.add_level([self._port_poller])
        if self._do_boot:
            # add the ready command no matter what
            cmd = self._get_ssh_ready_cmd()
            cloudinitd.log(self._log, logging.DEBUG, "Adding a ssh poller %s " % (cmd))
            self._ssh_poller = PopenExecutablePollable(cmd, log=self._log, callback=self._context_cb, timeout=self._s.pgm_timeout, allowed_errors=2)
            self._pollables.add_level([self._ssh_poller])

            # if already contextualized, dont do it again (could be problematic).  we probably need to make a rule
            # the contextualization programs MUST handle multiple executions, but we can be as helpful as possible
            if self._s.state == cloudinitd.service_state_contextualized:
                cloudinitd.log(self._log, logging.DEBUG, "%s is already contextualized" % (self.name))
            else:
                if self._s.bootpgm:
                    cmd = self._get_boot_cmd()
                    cloudinitd.log(self._log, logging.DEBUG, "%s running the boot pgm command %s" % (self.name, cmd))
                    self._boot_poller = PopenExecutablePollable(cmd, log=self._log, allowed_errors=0, callback=self._context_cb, timeout=self._s.pgm_timeout, done_cb=self.context_done_cb)
                    self._pollables.add_level([self._boot_poller])
                else:
                    self.context_done_cb(None)
                    cloudinitd.log(self._log, logging.DEBUG, "%s has no boot conf" % (self.name))
        else:
            cloudinitd.log(self._log, logging.DEBUG, "%s skipping the boot" % (self.name))

        if self._do_ready:
            cmd = self._get_ssh_ready_cmd()
            self._ssh_poller2 = PopenExecutablePollable(cmd, log=self._log, callback=self._context_cb, allowed_errors=2)
            self._pollables.add_level([self._ssh_poller2])
            if self._s.readypgm:
                cmd = self._get_readypgm_cmd()
                cloudinitd.log(self._log, logging.DEBUG, "%s running the ready pgm command %s" % (self.name, cmd))
                self._ready_poller = PopenExecutablePollable(cmd, log=self._log, allowed_errors=1, callback=self._context_cb, timeout=self._s.pgm_timeout)
                self._pollables.add_level([self._ready_poller])
            else:
                cloudinitd.log(self._log, logging.DEBUG, "%s has no ready program" % (self.name))
        else:
            cloudinitd.log(self._log, logging.DEBUG, "%s skipping the readypgm" % (self.name))
        self._pollables.start()

    @cloudinitd.LogEntryDecorator
    def _get_fab_command(self):
        fabexec = "fab"
        try:
            if os.environ['CLOUDINITD_FAB']:
                fabexec = os.environ['CLOUDINITD_FAB']
        except:
            pass
        fabfile = str(bootfabtasks.__file__).strip()
        cloudinitd.log(self._log, logging.DEBUG, "raw fabfileis: |%s|" % (fabfile))
        if fabfile[-4:] == ".pyc":
            fabfile = fabfile[0:-4] + ".py"
            cloudinitd.log(self._log, logging.DEBUG, "modfiled fabfile is: %s" % (fabfile))
        key_str = ""
        if self._s.localkey:
            key_str = "-i %s" % (self._s.localkey)
        cmd = fabexec + " -f %s -D -u %s %s " % (fabfile, self._s.username, key_str)
        cloudinitd.log(self._log, logging.DEBUG, "fab command is: %s" % (cmd))
        return cmd

    @cloudinitd.LogEntryDecorator
    def get_scp_command(self, src, dst, upload=False, recursive=False, forcehost=None):
        scpexec = "scp"
        if 'CLOUDINITD_SCP' in os.environ:
            scpexec = os.environ['CLOUDINITD_SCP']
        if recursive:
            scpexec += " -r"
        key_str = ""
        if self._s.localkey:
            key_str = "-i %s" % (self._s.localkey)

        cmd = scpexec + " -o BatchMode=yes -o StrictHostKeyChecking=no -o PasswordAuthentication=no %s " % (key_str)
        hostname = self._expand_attr(self._s.hostname)
        if forcehost:
            hostname = forcehost
        user = ""
        if self._s.scp_username:
            user = "%s@" % (self._s.scp_username)
        if upload:
            cmd += "%s %s%s:%s" % (src, user, hostname, dst)
        else:
            cmd += "%s%s:%s %s" % (user, hostname, src, dst)
        return cmd

    @cloudinitd.LogEntryDecorator
    def get_scp_username(self):
        return self._s.scp_username

    @cloudinitd.LogEntryDecorator
    def _get_ssh_command(self, host):
        if not host:
            raise ConfigException("Trying to create an ssh command to a null hostname, something is not right.")
        sshexec = "ssh"
        try:
            if os.environ['CLOUDINITD_SSH']:
                sshexec = os.environ['CLOUDINITD_SSH']
        except:
            pass
        host = self._expand_attr(host)
        user = ""
        if self._s.username:
            user = "%s@" % (self._s.username)

        key_str = ""
        if self._s.localkey:
            key_str = "-i %s" % (self._s.localkey)
        cmd = sshexec + "  -n -T -o BatchMode=yes -o StrictHostKeyChecking=no -o PasswordAuthentication=no %s %s%s" % (key_str, user, host)
        return cmd

    @cloudinitd.LogEntryDecorator
    def get_db_id(self):
        return self._s.id

    def __str__(self):
        return self.name

    @cloudinitd.LogEntryDecorator
    def get_dep(self, key):
        # first parse through the known ones, then hit the attr bag
        if key == "hostname":
            rc = self._s.hostname
        elif key == "instance_id":
            rc = self._s.instance_id
        elif key == "run_name":
            rc = self.run_name
        else:
            try:
                rc = self._attr_bag[key]
            except Exception, ex:
                # if it isn't in the attr bag pull it from the services db defs.  This should allow the user the ability
                # to query everything about the service
                try:
                    rc = self._s.__getattribute__(key)
                except AttributeError:
                    raise ConfigException("The service %s has no attr by the name of %s.  Please check your config files. %s" % (self._myname, key, str(ex)), ex)
        if rc:
            rc = str(rc)
            rc = self._expand_attr(rc)
        return rc

    @cloudinitd.LogEntryDecorator
    def get_dep_keys(self):
        # first parse through the known ones, then hit the attr bag
        keys = ["hostname", "instance_id"] + self._attr_bag.keys()
        return keys

    @cloudinitd.LogEntryDecorator
    def _expand_attr_list(self, val):
        if not val:
            return val

        val = str(val)
        val_a = shlex.split(val)
        cmd_args = []

        for v in val_a:
            new_v = self._expand_attr(v)
            cmd_args.append(new_v)

        return " ".join(pipes.quote(s) for s in cmd_args)

    @cloudinitd.LogEntryDecorator
    def _expand_attr(self, val):
        if not val:
            return val
        pattern = re.compile('\$\{(.*?)\.(.*?)\}')

        match = pattern.search(val)
        while match:
            svc_name = match.group(1)
            attr_name = match.group(2)
            if svc_name:
                if svc_name == "global":
                    subs = get_global(attr_name, raise_ex=True)
                else:
                    subs = self._top_level.find_dep(svc_name, attr_name)
            else:
                subs = self.get_dep(attr_name)

            ndx = val.find(match.group(0)) + len(match.group(0))
            if subs is not None:
                val = val.replace(match.group(0), subs)
            match = pattern.search(val[ndx:])
        return val

    @cloudinitd.LogEntryDecorator
    def _do_attr_bag(self):

        for bao in self._s.attrs:
            val = bao.value
            self._attr_bag[bao.key] = self._expand_attr(val)

    @cloudinitd.LogEntryDecorator
    def restart(self, boot, ready, terminate, callback=None):
        # terminate should have to be true here
        if self._running:
            raise APIUsageException("This SVC object was already started.  wait for it to complete and try restart")
        self._restart_count = self._restart_count + 1
        if self._restart_count > self._restart_limit:
            emsg = "Retry on error count exceeded (%d)" % (self._restart_count)
            cloudinitd.log(self._log, logging.ERROR, emsg, tb=traceback)
            raise APIUsageException(emsg)

        if callback is None:
            callback = self._callback
        self._validate_and_reinit(boot=boot, ready=ready, terminate=terminate, callback=callback, repair=True)
        self._start()

    @cloudinitd.LogEntryDecorator
    def start(self):
        if self._running:
            raise APIUsageException("This SVC object was already started.  wait for it to complete and try restart")

        if self._s.state == cloudinitd.service_state_terminated and not self._do_boot and not self._do_terminate:
            ex = APIUsageException("the service %s has been terminated.  The only action that can be performed on it is a boot" % (self.name))
            if not self._execute_callback(cloudinitd.callback_action_error, str(ex), ex):
                raise ex
        Pollable.start(self)
        self._start()

    @cloudinitd.LogEntryDecorator
    def _start(self):
        Pollable.start(self)

        self._running = True
        # load up deps.  This must be delayed until start is called to ensure that previous levels have the populated
        # values
        try:

            if self._term_host_pollers and not self._iass_started:
                self.pre_start_iaas()
            self._term_host_pollers.start()
            self._execute_callback(cloudinitd.callback_action_started, "Started %s" % (self.name))
        except Exception, ex:
            self._running = False
            if not self._execute_callback(cloudinitd.callback_action_error, str(ex), ex):
                cloudinitd.log(self._log, logging.ERROR, str(ex), tb=traceback)
                raise

    @cloudinitd.LogEntryDecorator
    def _execute_callback(self, state, msg, ex=None):
        self.last_exception = ex
        self.exception_list.append(ex)
        if not self._callback:
            return False
        rc = self._callback(self, state, msg)
        if state != cloudinitd.callback_action_error:
            return False
        if rc == cloudinitd.callback_return_restart:
            if self._restart_count > self._restart_limit:
                return False
            self._running = False
            self.restart(boot=True, ready=True, terminate=True, callback=self._callback)
            return True
        return False

    @cloudinitd.LogEntryDecorator
    def poll(self):
        Pollable.poll(self)

        try:
            rc = self._poll()
            if rc:
                self._running = False
            return rc
        except MultilevelException, multiex:
            msg = ""
            stdout = ""
            stderr = ""
            if self._ssh_poller in multiex.pollable_list:
                msg = "Service %s error getting ssh access to %s" % (self._myname, self._s.hostname)
                stdout = self._ssh_poller.get_stdout()
                stderr = self._ssh_poller.get_stderr()
            if self._ssh_poller2 in multiex.pollable_list:
                msg = "Service %s error getting ssh access to %s." % (self._myname, self._s.hostname)
                stdout = self._ssh_poller2.get_stdout()
                stderr = self._ssh_poller2.get_stderr()
            if self._boot_poller in multiex.pollable_list:
                msg = "Service %s error configuring for boot: %s\n%s" % (self._myname, self._s.hostname, msg)
                stdout = self._boot_poller.get_stdout()
                stderr = self._boot_poller.get_stderr()
            if self._ready_poller in multiex.pollable_list:
                msg = "Service %s error running ready program: %s\n%s" % (self._myname, self._s.hostname, msg)
                stdout = self._ready_poller.get_stdout()
                stderr = self._ready_poller.get_stderr()
            if self._shutdown_poller in multiex.pollable_list:
                msg = "Service %s error running shutdown on iaas: %s\n%s" % (self._myname, self._s.hostname, msg)
                stdout = ""
                stderr = ""
            if self._rmdir_poller in multiex.pollable_list:
                msg = "Service %s error running rmdir program on: %s\n%s" % (self._myname, self._s.hostname, msg)
                stdout = self._rmdir_poller.get_stdout()
                stderr = self._rmdir_poller.get_stderr()
            if self._terminate_poller in multiex.pollable_list:
                msg = "Service %s error running terminate program on: %s\n%s" % (self._myname, self._s.hostname, msg)
                stdout = self._terminate_poller.get_stdout()
                stderr = self._terminate_poller.get_stderr()

            if self._port_poller in multiex.pollable_list:
                msg = "the poller that attempted to connect to the ssh port on %s failed for %s\n%s" % (self._s.hostname, self._myname, msg)
                stdout = ""
                stderr = ""

            self._running = False
            if not self._execute_callback(cloudinitd.callback_action_error, msg, multiex):
                raise ServiceException(multiex, self, msg, stdout, stderr)
            return False
        except Exception, ex:
            cloudinitd.log(self._log, logging.ERROR, "%s" %(str(ex)), traceback)
            self._s.last_error = str(ex)
            self._db.db_commit()
            self._running = False
            if not self._execute_callback(cloudinitd.callback_action_error, str(ex), ex):
                raise ServiceException(ex, self)
            return False

    @cloudinitd.LogEntryDecorator
    def _log_poller_output(self, poller):
        if not poller:
            return
        try:
            stdout = poller.get_stdout()
            stderr = poller.get_stderr()
            cmd = poller.get_command()
            # this is reapeated info but at a convient location.
            cloudinitd.log(self._log, logging.DEBUG, "Output for the command %s:\nstdout\n------\n%s\nstderr\n------\n%s" % (cmd, stdout, stderr))
        except Exception, ex:
            cloudinitd.log(self._log, logging.ERROR, "Failed to log output info | %s" % (str(ex)))

    @cloudinitd.LogEntryDecorator
    def _context_cb(self, popen_poller, action, msg):
        if action == cloudinitd.callback_action_transition:
            self._execute_callback(action, msg)

    @cloudinitd.LogEntryDecorator
    def _poll(self):
        if not self._running:
            return True
        # if we already have a hostname move onto polling the fab tasks
        if not self._term_host_pollers:
            cloudinitd.log(self._log, logging.DEBUG, "No terminate pollers in _poll")
            if not self._pollables:
                self._make_pollers()
            rc = self._pollables.poll()
            if rc:
                self._running = False
                self._execute_done_cb()  # on parent object for timings mostly
                self._execute_callback(cloudinitd.callback_action_complete, "Service Complete")
                poller_list = [self._ssh_poller, self._ssh_poller2, self._boot_poller, ]
                for p in poller_list:
                    cloudinitd.log(self._log, logging.DEBUG, "Getting the output of %s" % (str(p)))
                    self._log_poller_output(p)
                self._clean_up()

            return rc

        if self._term_host_pollers.poll():
            self._term_host_pollers = None
        return False

    @cloudinitd.LogEntryDecorator
    def _read_boot_output(self):
        """
        Read in the output of the bootpgm to the attr bag
        """
        if not self._boot_output_file:
            return
        try:
            with open(self._boot_output_file, "r") as f:
                j_doc = json.load(f)
        except Exception, ex:
            cloudinitd.log(self._log, logging.DEBUG, "No output read from the boot program %s" % (str(ex)))
            return
        for k in j_doc.keys():
            self._attr_bag[k] = j_doc[k]
            bao = BagAttrsObject(k, j_doc[k])
            self._s.attrs.append(bao)

    @cloudinitd.LogEntryDecorator
    def context_done_cb(self, poller):
        self._read_boot_output()
        self._s.state = cloudinitd.service_state_contextualized
        self._db.db_commit()
        cloudinitd.log(self._log, logging.DEBUG, "%s hit context_done_cb callback" % (self.name))

    @cloudinitd.LogEntryDecorator
    def _hostname_poller_done(self, poller):
        self._s.hostname = self._hostname_poller.get_hostname()
        self._db.db_commit()
        self._execute_callback(cloudinitd.callback_action_transition, "Have hostname %s" % self._s.hostname)
        cloudinitd.log(self._log, logging.DEBUG, "%s hit _hostname_poller_done callback instance %s" % (self.name, self._s.instance_id))

    @cloudinitd.LogEntryDecorator
    def get_ssh_command(self):
        return self._get_ssh_command(self._s.hostname)

    @cloudinitd.LogEntryDecorator
    def _get_directory_cleanup_cmd(self):
        host = self._expand_attr(self._s.hostname)
        cmd = self._get_fab_command() + " cleanup_dirs:hosts=%s,stagedir=%s,local_exe=%s" % (host, self._stagedir, (self._s.local_exe))
        cloudinitd.log(self._log, logging.DEBUG, "Using cleanup pgm command %s" % (cmd))
        return cmd

    @cloudinitd.LogEntryDecorator
    def _get_ssh_ready_cmd(self):
        true_pgm = "true"
        if self._s.local_exe:
            return true_pgm

        cmd = self._get_ssh_command(self._s.hostname) + " " + true_pgm
        cloudinitd.log(self._log, logging.DEBUG, "Using ssh command %s" % (cmd))
        return cmd

    @cloudinitd.LogEntryDecorator
    def _get_readypgm_cmd(self):
        host = self._expand_attr(self._s.hostname)
        readypgm = self._expand_attr(self._s.readypgm)
        readypgm_args = self._expand_attr_list(self._s.readypgm_args)

        if readypgm_args:
            readypgm_args = urllib.quote(readypgm_args)

        cmd = self._get_fab_command() + " 'readypgm:hosts=%s,pgm=%s,args=%s,stagedir=%s,local_exe=%s'" % (host, readypgm, readypgm_args, self._stagedir, str(self._s.local_exe))
        cloudinitd.log(self._log, logging.DEBUG, "Using ready pgm command %s" % (cmd))
        return cmd

    @cloudinitd.LogEntryDecorator
    def _get_boot_cmd(self):
        host = self._expand_attr(self._s.hostname)

        bootpgm = self._expand_attr(self._s.bootpgm)
        bootpgm_args = self._expand_attr_list(self._s.bootpgm_args)
        if bootpgm_args:
            bootpgm_args = urllib.quote(bootpgm_args)

        (osf, self._boot_output_file) = tempfile.mkstemp()
        os.close(osf)

        bootconf = None
        bootenv_file = None
        if self._s.bootconf:
            bootconf = self._fill_template(self._s.bootconf)
            try:
                bootenv_file = self._bootconf_to_env(bootconf)
            except Exception:
                cloudinitd.log(self._log, logging.WARN, "Failed to convert bootconf to env file", tb=traceback)
                bootenv_file = None

        cmd = self._get_fab_command() + " 'bootpgm:hosts=%s,pgm=%s,args=%s,conf=%s,env_conf=%s,output=%s,stagedir=%s,remotedir=%s,local_exe=%s'" % (host, bootpgm, bootpgm_args,  bootconf, bootenv_file, self._boot_output_file, self._stagedir, get_remote_working_dir(), str(self._s.local_exe))
        cloudinitd.log(self._log, logging.DEBUG, "Using boot pgm command %s" % (cmd))
        return cmd

    @cloudinitd.LogEntryDecorator
    def _get_termpgm_cmd(self):
        host = self._expand_attr(self._s.hostname)
        terminatepgm = self._expand_attr(self._s.terminatepgm)
        terminatepgm_args = self._expand_attr_list(self._s.terminatepgm_args)

        if terminatepgm_args:
            terminatepgm_args = urllib.quote(terminatepgm_args)

        cmd = self._get_fab_command() + " readypgm:hosts=%s,pgm=%s,args=%s,stagedir=%s,local_exe=%s" % (host, terminatepgm, terminatepgm_args, self._stagedir, str(self._s.local_exe))
        cloudinitd.log(self._log, logging.DEBUG, "Using terminate pgm command %s" % (cmd))
        return cmd

    @cloudinitd.LogEntryDecorator
    def _fill_template(self, path):

        if not os.path.exists(path):
            raise ConfigException("template file does not exist: %s" % path)

        f = open(path)
        doc_tpl = f.read()
        f.close()

        template = string.Template(doc_tpl)
        try:
            document = template.substitute(self._attr_bag)
        except Exception, e:
            raise ConfigException("The file '%s' has a variable that could not be found: %s" % (path, str(e)))

        # having the template name in the temp file name makes it easier
        # to identify
        prefix = self.name + "_" + os.path.basename(path)
        prefix += "_"
        if self._logfile is None:
            dir = None
        else:
            dir = os.path.dirname(self._logfile)

        (fd, newpath) = tempfile.mkstemp(prefix=prefix, text=True, dir=dir)
        os.close(fd)

        f = open(newpath, 'w')
        f.write(document)
        f.close()

        return newpath

    @cloudinitd.LogEntryDecorator
    def _bootconf_to_env(self, path):

        vals_dict = self._load_dict_from_file(path)

        prefix = os.path.basename(path)
        prefix += "_"
        if self._logfile is None:
            dir = None
        else:
            dir = os.path.dirname(self._logfile)
        (fd, newpath) = tempfile.mkstemp(prefix=prefix, text=True, dir=dir)
        os.close(fd)
        outf = open(newpath, "w")
        for v in vals_dict:
            line = 'export %s="%s"' % (v, vals_dict[v])
            outf.write(line)
            outf.write(os.linesep)
        outf.close()

        return newpath

    def _load_dict_from_file(self, path):

        #TODO support yaml directly?
        with open(path, "r") as f:
            d = json.load(f)

        return d

    @cloudinitd.LogEntryDecorator
    def cancel(self):
        if self._pollables:
            self._pollables.cancel()
        if self._term_host_pollers:
            self._term_host_pollers.cancel()

    @cloudinitd.LogEntryDecorator
    def new_iaas_instance(self, instance):
        h = IaaSHistoryObject(instance.get_id())
        self._db.db_obj_add(h)
        self._db.db_commit()
        self._s.history.append(h)

    @cloudinitd.LogEntryDecorator
    def generate_attr_doc(self):
        json_doc = {}
        keys = self.get_dep_keys()
        for k in keys:
            json_doc[k] = self.get_dep(k)
        # now we have to get all the keys not in the list
        db_keys = [
            'image',
            'iaas',
            'allocation',
            'keyname',
            'localkey',
            'username',
            'scp_username',
            'readypgm',
            'hostname',
            'bootconf',
            'bootpgm',
            'securitygroups',
            'instance_id',
            'iaas_url',
            'iaas_key',
            'iaas_secret',
            'state',
            'terminatepgm',
            'iaas_launch'
            ]
        for k in db_keys:
            json_doc[k] = self.get_dep(k)
        return json_doc
