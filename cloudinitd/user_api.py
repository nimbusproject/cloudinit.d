# This API allows user to manage services in multiple clouds.  It can
# launch/terminate/and report status on an entire boot plan.
#
# A boot plan is a series of levels that are run in serial.  Each subsequent
# level depends on attributes of the previous and can thus not be started
# until the previous completes.
#
# Each level contains a set of services to run.  All services in a level
# can be started at the same time and have no dependency on each other.
# As a loose description, a service is a process running on a remote
# machine.  Often times part of starting the service includes launching
# a IaaS VM and configuring it, but this is not strictly needed.  Services
# can be started on existing machines as well.
#
# When a user creates a boot plan they describe each service with three
# major parts:
#  1) a VM image to launch OR an IP address where the service will be run
#  2) a contextualization document.  This is enough information to configure
#     the machine and run the needed services.
#  3) a ready program.  This is a script that verifies the service is up
#     and ready to go.
#
#  The configuration is described in detail elsewhere.  Here we show
#  the API for launching/terminating and gathering status for a bootplan
from cloudinitd.services import SVCContainer

import os
import uuid
import time
import logging
import stat
import cb_iaas
from cloudinitd.exceptions import APIUsageException, ServiceException
from cloudinitd.persistence import CloudInitDDB
from cloudinitd.services import BootTopLevel
import cloudinitd


class CloudInitD(object):
    """
        This class is the top level boot description. It holds the parent Multilevel boot object which contains a set
        of many pollables.  The object also contains a way to get variable information from every service created.
        A service cannot be created without this object.  This object holds a dictionary of all services which is
        used for querying dependencies
    """

    def __init__(self, db_dir, config_file=None, db_name=None, log_level="warn", logdir=None, level_callback=None, service_callback=None, boot=True, ready=True, terminate=False, continue_on_error=False, fail_if_db_present=False):
        """
        db_dir:     a path to a directories where databases can be stored.

        config_file: the top_level config file describing this boot plan.
                    if this parameter is given then it is assumed that this
                    is a new launch plan.  if it is not given the db_name
                    parameter is required and the plan is loaded from an
                    existing database

        db_name:    the name of the database.  this is not an actual path
                    to a file, it is the run name given when the plan is
                    launched.  The run name can be found in self.name

        level_callback: a callback function that is invoked whenever
                        a level completes or a new level is started.  The signature of the callback is:

                        def func_name(cloudinitd, action, current_level)

                        action is a string from the set
                        ["starting", "transition", "complete", "error"]

        service callback: a callbackfunciton that is invoked whenever
                        a service is started, progresses, or finishes.  The signature is:

                        def func_name(cloudservice, action, msg)

                        action is a string from the set:

                        ["starting", "transition", "complete", "error"]

        boot=True: instructs the object to contextualized the service or now

        ready=True: instructs the service to run the ready program or not

        terminate=False: instructs the service to run the shutdown program or not

        fail_if_db_present=False: instructs the constructor that the caller expects DB present already

        When this object is configured with a config_file a new sqlite
        database is created under @db_dir and a new name is picked for it.
        the data base ends up being called <db_dir>/cloudinitd-<name>.db,
        but the user has no real need to know this.

        The contructor does not actually launch a run.  It simply loads up
        the database with the information in the config file (in the case
        of a new launch) and then builds the inmemory data structures.
        """

        if not db_name and not config_file:
            raise APIUsageException("Cloud boot must have a db_name or a config file to load")
        if not os.path.exists(db_dir):
            raise APIUsageException("Path to the db directory does not exist: %s" % (db_dir))

        self._level_callback = level_callback
        self._service_callback = service_callback

        if not db_name:
            db_name = str(uuid.uuid4()).split("-")[0]

        db_file = "cloudinitd-%s.db" % db_name
        db_path = os.path.join("/", db_dir, db_file)
        self._db_path = db_path
        if config_file is None:
            if not os.path.exists(db_path):
                raise APIUsageException("Path to the db does not exist %s.  New dbs must be given a config file" % (db_path))

        if fail_if_db_present and os.path.exists(db_path):
            raise APIUsageException("Already exists: '%s'" % db_path)

        (self._log, logfile) = cloudinitd.make_logger(log_level, db_name, logdir=logdir)

        self._started = False
        self.run_name = db_name
        dburl = "sqlite:///%s" % (db_path)

        self._db = CloudInitDDB(dburl)
        os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
        if config_file:
            self._bo = self._db.load_from_conf(config_file)
        else:
            self._bo = self._db.load_from_db()

        self._levels = []
        self._boot_top = BootTopLevel(log=self._log, level_callback=self._mp_cb, service_callback=self._svc_cb, boot=boot, ready=ready, terminate=terminate, continue_on_error=continue_on_error)
        for level in self._bo.levels:
            level_list = []
            for s in level.services:
                try:
                    (s_log, logfile) = cloudinitd.make_logger(log_level, self.run_name, logdir=logdir, servicename=s.name)

                    svc = self._boot_top.new_service(s, self._db, log=s_log, logfile=logfile, run_name=self.run_name)

                    # if boot is not set we assume it was already booted and we expand
                    if not boot:
                        svc._do_attr_bag()
                    level_list.append(svc)
                except Exception, svcex:
                    if not continue_on_error:
                        raise
                    action = cloudinitd.callback_action_error
                    msg = "ERROR creating SVC object %s, but continue on error set: %s" % (s.name, str(svcex))
                    if self._service_callback:
                        cs = CloudService(self, None, name=s.name)
                        self._service_callback(self, cs, action, msg)

                    cloudinitd.log(self._log, logging.ERROR, msg)

            self._boot_top.add_level(level_list)
            self._levels.append(level_list)
        self._exception = None
        self._last_exception = None
        self._exception_list = []

    @cloudinitd.LogEntryDecorator
    def find_dep(self, service_name, key):
        return self._boot_top.find_dep(service_name, key)

    @cloudinitd.LogEntryDecorator
    def get_db_file(self):
        """
        Return the path to the db file in use.
        """
        return self._db_path

    @cloudinitd.LogEntryDecorator
    def _mp_cb(self, mp, action, level_ndx):
        if self._level_callback:
            self._level_callback(self, action, level_ndx)

    @cloudinitd.LogEntryDecorator
    def _svc_cb(self, svc, action, msg):
        self._last_exception = svc.last_exception
        rc = cloudinitd.callback_return_default
        if action == cloudinitd.callback_action_error:
            self._exception = svc.last_exception
        if self._service_callback:
            rc = self._service_callback(self, CloudService(self, svc), action, msg)
        return rc

    @cloudinitd.LogEntryDecorator
    def cancel(self):
        """
        Request to cancel the running shutdown or start action.  The cancel is nonblocking and the user should
        continue to call poll()
        """
        self._boot_top.cancel()

    @cloudinitd.LogEntryDecorator
    def get_all_services(self):
        """
        Get a list of all CloudServices associated with this boot plan.  A CloudService object can be used to
        inspect the state of a specific service in the plan.
        """
        svc_list = self._boot_top.get_services()
        cs_list = [CloudService(self, svc[1]) for svc in svc_list]
        return cs_list

    # return a booting service for inspection by the user
    @cloudinitd.LogEntryDecorator
    def get_service(self, svc_name):
        """
        Get a specific CloudService object by name.  The name corresponds to the section [svc-<name>] in
        the plan.
        """
        svc = self._boot_top.get_service(svc_name)
        return CloudService(self, svc)

    # get a list of all the services in the given level
    @cloudinitd.LogEntryDecorator
    def get_level(self, level_ndx):
        svc_list = self._levels[level_ndx]
        cs_list = [CloudService(self, svc) for svc in svc_list]
        return cs_list

    @cloudinitd.LogEntryDecorator
    def get_level_count(self):
        return len(self._levels)

    # poll the entire boot config until complete
    @cloudinitd.LogEntryDecorator
    def block_until_complete(self, poll_period=0.5):
        """
        poll_period:        the time to wait in between calls to poll()

        This method is just a convenience loop around calls to poll.
        """
        if not self._started:
            raise APIUsageException("Boot plan must be started first.")

        done = False
        while not done:
            done = self.poll()
            if not done:
                time.sleep(poll_period)

        self._db.db_commit()

    # poll one pass at the boot plan.
    @cloudinitd.LogEntryDecorator
    def poll(self):
        """
        poll the launch plan.  This will through an exception if the
        start() has not yet been called.  An exception will also be
        thrown if any service experiences an error.  When this occurs
        the user can use the status() method to find exactly what went
        wrong.

        This will return False until the boot/ready test has completed
        either successfully or with an error.
        """
        if not self._started:
            raise APIUsageException("Boot plan must be started first.")
        rc = self._boot_top.poll()
        if rc:
            self._bo.status = 1
            self._db.db_commit()
        return rc

    @cloudinitd.LogEntryDecorator
    def start(self):
        """
        Begin launch plan.  If this is a new launch VMs will be started
        and boot configuration will occur before running the ready programs.
        If the services were already booted, just the ready program is run
        to test that everything is still working.

        This is an asynchronous call.  it just starts the process, poll()
        or block until complete must be called to check the status.

        After exeriencing an error a call to start can be made again.
        This will not restart any services.  That is up to the user
        to do by getting the failed services from error_status() and
        restarting them.  A call to start will always walk the list
        of levels in order.  It will start VM instances that have not
        yet been started, contextializes VMs tha thave not yet been
        contextualized, and call the ready program for all services.
        """

        self._boot_top.start()
        self._started = True

    @cloudinitd.LogEntryDecorator
    def pre_start_iaas(self):
        bo = self._bo
        for level in bo.levels:
            for s in level.services:
                svc = self._boot_top.get_service(s.name)
                svc.pre_start_iaas()

    @cloudinitd.LogEntryDecorator
    def boot_validate(self):
        bo = self._bo
        connnections = {}
        for level in bo.levels:
            for s in level.services:
                svc = self._boot_top.get_service(s.name)

                cb_iaas.iaas_validate(svc, self._log)

                hash_str = ""
                iaas_url = svc.get_dep("iaas_url")
                if iaas_url:
                    hash_str = hash_str + iaas_url
                hash_str = hash_str + "/"
                iaas = svc.get_dep("iaas")
                if iaas:
                    hash_str = hash_str + iaas
                hash_str = hash_str + "/"
                key = svc.get_dep("iaas_key")
                if key:
                    hash_str = hash_str + key
                hash_str = hash_str + "/"
                secret = svc.get_dep("iaas_secret")
                if secret:
                    hash_str = hash_str + secret

                if hash_str not in connnections.keys():
                    con = cb_iaas.iaas_get_con(svc, key=key, secret=secret, iaasurl=iaas_url)
                    #con = cb_iaas.iaas_get_con(svc)
                    connnections[hash_str] = (con, [svc])
                else:
                    (con, svc_list) = connnections[hash_str]
                    svc_list.append(svc)

        exception_list = []
        for (con, svc_list) in connnections.values():
            try:
                con.get_all_instances()
            except Exception, ex:
                # this means that there is a problem connection with all the associated services
                names = ""
                d = ""
                for svc in svc_list:
                    exception_list.append((svc, ex,))
                    names = names + d + svc.name
                    d = ","
                msg = "The following services have problems with their IaaS configuration.  Please check the launch plan to verify the iaas configuration is correct. %s || %s" % (names, str(ex))
                cloudinitd.log(self._log, logging.ERROR, msg)
        return exception_list

    @cloudinitd.LogEntryDecorator
    def shutdown(self, dash_nine=False):
        self._boot_top.reverse_order()
        self._boot_top.start()
        self._started = True

    @cloudinitd.LogEntryDecorator
    def get_exception(self):
        return self._exception

    @cloudinitd.LogEntryDecorator
    def get_all_exceptions(self):
        return self._exception_list

    @cloudinitd.LogEntryDecorator
    def get_last_exception(self):
        return self._last_exception

    @cloudinitd.LogEntryDecorator
    def get_iaas_history(self):
        ha = self._db.get_iaas_history()

        l = []
        for h in ha:
            svc = SVCContainer(self._db, h.service, None, log=self._log, boot=False, ready=True, terminate=False)
            con = cb_iaas.iaas_get_con(svc)
            try:
                inst = con.find_instance(h.instance_id)
            except:
                inst = None
            i = IaaSHistory(inst, h.instance_id, svc)
            l.append(i)
        return l

    @cloudinitd.LogEntryDecorator
    def get_json_doc(self):
        return self._boot_top.get_json_doc()

    @cloudinitd.LogEntryDecorator
    def get_level_runtime(self, level_ndx):
        return self._boot_top.get_level_runtime(level_ndx-1)


class IaaSHistory(object):

    def __init__(self, inst, id, svc):
        self._inst = inst
        self._id = id
        self._svc = svc

    @cloudinitd.LogEntryDecorator
    def get_service_name(self):
        return self._svc.name

    @cloudinitd.LogEntryDecorator
    def get_context_state(self):
        return self._svc._s.state

    @cloudinitd.LogEntryDecorator
    def get_service_iaas_handle(self):
        return self._svc._s.instance_id

    @cloudinitd.LogEntryDecorator
    def get_state(self):
        if self._inst:
            return self._inst.get_state()
        return "unknown"

    @cloudinitd.LogEntryDecorator
    def get_id(self):
        return self._id

    @cloudinitd.LogEntryDecorator
    def terminate(self):
        if self._inst:
            self._inst.terminate()


class CloudService(object):

    def __init__(self, cloudbooter, svc, name=None):
        """This should only be called by the CloudInitD object"""
        self._svc = svc
        if svc is None:
            self.name = name
        else:
            self.name = svc.name
        self._cb = cloudbooter
        self._db = cloudbooter._db

    @cloudinitd.LogEntryDecorator
    def get_iaas_status(self):
        """If the associated service is run in a VM that cloudinit.d launched, this will return the
            IaaS status of that VM"""
        return self._svc.get_iaas_status()

    @cloudinitd.LogEntryDecorator
    def get_keys_from_bag(self):
        if self._svc is None:
            raise APIUsageException("This Cloud service has no real backing service")
        return self._svc.get_dep_keys()

    @cloudinitd.LogEntryDecorator
    def get_runtime(self):
        return self._svc.get_runtime()

    @cloudinitd.LogEntryDecorator
    def get_attr_from_bag(self, name):
        if self._svc is None:
            raise APIUsageException("This Cloud service has no real backing service")
        return self._svc.get_dep(name)
    # need various methods for monitoring state. values from attr bag and from db

    @cloudinitd.LogEntryDecorator
    def shutdown(self, callback=None):
        """
        This will call the remote shutdown program associate with the
        service.  It is called asynchronously.  Poll just be called
        to make sure it have completed.

        if dash_nine is True the shutdown function will be skipped and
        the IaaS instance will be terminate (if the service has an
        IaaS instance.

        returns an pollable object
        """
        if self._svc is None:
            raise APIUsageException("This Cloud service has no real backing service")
        self._svc.restart(boot=False, ready=False, terminate=True, callback=callback)
        return self._svc

    @cloudinitd.LogEntryDecorator
    def restart(self):
        """
        This will restart the service, or check the results of the ready
        program if the service is already running.
        """
        if self._svc is None:
            raise APIUsageException("This Cloud service has no real backing service")
        self._svc.restart(boot=True, ready=True, terminate=True)
        return self._svc

    @cloudinitd.LogEntryDecorator
    def get_ssh_command(self):
        if self._svc is None:
            raise APIUsageException("This Cloud service has no real backing service")
        return self._svc.get_ssh_command()

    @cloudinitd.LogEntryDecorator
    def get_scp_command(self, src, dst, upload=False, recursive=False, forcehost=None):
        if self._svc is None:
            raise APIUsageException("This Cloud service has no real backing service")
        return self._svc.get_scp_command(src, dst, upload=upload, recursive=recursive, forcehost=forcehost)

    @cloudinitd.LogEntryDecorator
    def get_scp_username(self):
        if self._svc is None:
            raise APIUsageException("This Cloud service has no real backing service")
        return self._svc.get_scp_username()


class CloudServiceException(ServiceException):
    def __init__(self, ex, svc):
        ServiceException.__init__(self, ex, svc)
        self.service = CloudService(svc)

