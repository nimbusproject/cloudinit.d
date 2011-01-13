# This API allows user to manage services in multiple clouds.  It can
# launch/terminate/and report status on an entire boot plan.
#
# a boot plan is a series of levels that are run in serial.  each subsequent
# level depends on attributes of the previous and can thus not be started
# until the previous completes.
#
# each level contains a set of services to run.  All serices in a level
# can be started at the same time and have no dependency on each other.
# as a loose description, a service is a process running on a remote
# machine.  Often times part of starting the service includes launching
# a IaaS VM and configuring it, but this is not strictly needed.  Services
# can be started on existing machines as well.
#
# when a user creates a boot plan they describe each service with three
# major parts:
#  1) a VM image to launch OR an IP address where the service will be run
#  2) a contextualization document.  This is enough information to configure
#     the machine and run the needed services.
#  3) a ready program.  This is a script that verifies the service is up
#     and ready to go.
#
#  The configuration is described in detail elsewhere.  Here we show
#  the API for launching/terminating and gathering status for a bootplan

import os
import uuid
import time
import logging
import stat
from cloudboot.exceptions import APIUsageException, PollableException, ServiceException
from cloudboot.persistence import CloudBootDB, ServiceObject
from cloudboot.pollables import NullPollable, MultiLevelPollable
from cloudboot.services import BootTopLevel, SVCContainer
import cloudboot

__author__ = 'bresnaha'



class CloudBoot(object):
    """
        This class is the top level boot description. It holds the parent Multilevel boot object which contains a set
        of many pollables.  The object also contains a way to get variable information from every service created.
        A service cannot be created without this object.  This object holds a dictionary of all services which is
        used for querying dependencies
    """
    
    def __init__(self, db_dir, config_file=None, db_name=None, log=logging, level_callback=None, service_callback=None, boot=True, ready=True, terminate=False, continue_on_error=False):
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

                        def func_name(cloudboot, action, current_level)

                        action is a string from the set
                        ["starting", "transition", "complete", "error"]

        service callback: a callbackfunciton that is invoked whenever
                        a service is started, progresses, or finishes.  The signature is:

                        def func_name(cloudservice, action, msg)

                        action is a string from the set:

                        ["starting", "transition", "complete", "error"]

        boot=True: instructs the object to contextualized the service or now

        ready=True: instructs the service to run the ready program or not

        terminate=False:    instructs the service to run the shutdown program or not

        When this object is configured with a config_file a new sqlite
        database is created under @db_dir and a new name is picked for it.
        the data base ends up being called <db_dir>/cloudboot-<name>.db,
        but the user has no real need to know this.

        The contructor does not actually launch a run.  It simply loads up
        the database with the information in the config file (in the case
        of a new launch) and then builds the inmemory data structures.
        """

        if db_name == None and config_file == None:
            raise APIUsageException("Cloud boot must have a db_name or a config file to load")
        if not os.path.exists(db_dir):
            raise APIUsageException("Path to the give db does not exist: %s" % (db_name))

        self._level_callback = level_callback
        self._service_callback = service_callback

        if db_name == None:
            db_name = str(uuid.uuid4()).split("-")[0]

        db_path = "/%s/cloudboot-%s.db" % (db_dir, db_name)
        self._db_path = db_path
        if config_file == None:
            if not os.path.exists(db_path):
                raise APIUsageException("Path to the db does not exist %s.  New dbs must be given a config file" % (db_path))

        self._log = log
        self._started = False
        self.run_name = db_name
        dburl = "sqlite://%s" % (db_path)

        self._db = CloudBootDB(dburl)
        os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)
        if config_file != None:
            self._bo = self._db.load_from_conf(config_file)
        else:
            self._bo = self._db.load_from_db()

        self._levels = []
        self._boot_top = BootTopLevel(log=log, level_callback=self._mp_cb, service_callback=self._svc_cb, boot=boot, ready=ready, terminate=terminate, continue_on_error=continue_on_error)
        for level in self._bo.levels:
            level_list = []
            for s in level.services:
                svc = self._boot_top.new_service(s, self._db)
                level_list.append(svc)

            self._boot_top.add_level(level_list)
            self._levels.append(level_list)


    def get_db_file(self):
        return self._db_path

    def _mp_cb(self, mp, action, level_ndx):
        if self._level_callback:
            self._level_callback(self, action, level_ndx)

    def _svc_cb(self, svc, action, msg):
        rc = cloudboot.callback_return_default
        if self._service_callback:
            rc = self._service_callback(self, CloudService(self, svc), action, msg)
        return rc

    def cancel(self):
        self._boot_top.cancel()

    def get_all_services(self):
        svc_list = self._boot_top.get_services()
        cs_list = [CloudService(self, svc) for svc in svc_list]
        return cs_list

    # return a booting service for inspection by the user
    def get_service(self, svc_name):
        svc = self._boot_top.get_service(svc_name)
        return CloudService(self, svc)

    # get a list of all the services in the given level
    def get_level(self, level_ndx):
        svc_list = self._levels[level_ndx]
        cs_list = [CloudService(self, svc) for svc in svc_list]
        return cs_list

    def get_level_count(self):
        return len(self._levels)

    # poll the entire boot config until complete
    def block_until_complete(self, poll_period=0.5):
        """
        poll_period:        the time to wait inbetween calls to poll()

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

    def shutdown(self, dash_nine=False):
        self._boot_top.reverse_order()
        self._boot_top.start()
        self._started = True




class CloudService(object):

    def __init__(self, cloudbooter, svc):
        """This should only be called by the CloudBoot object"""
        self._svc = svc
        self.name = svc.name
        self._cb = cloudbooter
        self._db = cloudbooter._db

    def get_attr_from_bag(self, name):
        return self._svc.get_dep(name)
    # need various methods for monitoring state. values from attr bag and from db

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
        self._svc.restart(boot=False, ready=False, terminate=True, callback=callback)
        return self._svc

    def restart(self):
        """
        This will restart the service, or check the results of the ready
        program if the service is already running.
        """
        self._svc.restart(boot=True, ready=True, terminate=True)
        return self._svc



class CloudServiceException(ServiceException):
    def __init__(self, ex, svc):
        ServiceException.__init__(self, ex, svc)
        self.service = CloudService(svc)

