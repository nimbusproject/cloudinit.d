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

class CloudBoot(object):
    """
    This is the top level object.  it contains all of the information for
    a given boot plan
    """

    def __init__(self, db_dir, config_file=None, db_name=None, log=logging):
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


        When this object is configured with a config_file a new sqlite 
        database is created under @db_dir and a new name is picked for it.
        the data base ends up being called <db_dir>/cloudboot-<name>.db,
        but the user has no real need to know this.

        The contructor does not actually launch a run.  It simply loads up
        the database with the information in the config file (in the case
        of a new launch) and then builds the inmemory data structures.
        """
        pass

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
        pass

    def shutdown(self, dash_nine=False):
        """
        This does the opposite of start().  It terminates the services
        in reverse order by level.  It is asynchronous just like start.
        If dash_nine is true the shutdown program is skipped and the 
        IaaS terminate function is invoked (if the service has an 
        associated IaaS handle
        """
        pass

    def poll(self, level_callback=None, service_callback=None):
        """
        level_callback: a callback function that is invoked whenever
                        a level completes or a new level is started

        service callback: a callbackfunciton that is invoked whenever
                        a service is started, progresses, or finishes

        poll the launch plan.  This will through an exception if the 
        start() has not yet been called.  An exception will also be 
        thrown if any service experiences an error.  When this occurs
        the user can use the status() method to find exactly what went 
        wrong.

        This will return False until the boot/ready test has completed
        either successfully or with an error.

        The callback functions allow a user to monitor progress.
        """
        pass

    def block_until_complete(self, level_callback=None, service_callback=None, poll_period=0.1):
        """
        level_callback:     see poll()
        service_callback:   see poll()
        poll_period:        the time to wait inbetween calls to poll()

        This method is just a convenience loop around calls to poll.
        """
        pass

    def get_services(self):
        """
        Return an ordered lists of levels.  Each level is a list of 
        of CloudService objects.  Users can interspect state with this
        """
        pass

    def error_status(self):
        """
        Like get services, only return just the services that had errors.
        If a level had no errors an empty list will be returned in that 
        slot.
        """
        pass

class CloudService(object):
    """
    This object represents a single service in the boot plan.  It can 
    be used to inspect details about the object.  The get_attr_from_bag
    function allows the user to check out any value associated with the
    service.

    XXX TODO XXX make this enumeration
    """

    def __init__(self, svc):
        """This should only be called by the CloudBoot object"""
        pass

    def shutdown(self, dash_nine=False):
        """
        This will call the remote shutdown program associate with the 
        service.  It is called asynchronously.  Poll just be called
        to make sure it have completed.

        if dash_nine is True the shutdown function will be skipped and
        the IaaS instance will be terminate (if the service has an
        IaaS instance.
        """

    def start(self):
        """
        This will restart the service, or check the results of the ready
        program if the serviceis already running.
        """
        pass

    def poll(self, service_callback=None):
        """
        service_callback:   let the user monitor progress of the shutdown
        or the restart.

        This function returns True when complete, or False if more polling
        is needed.  Exceptions are thrown if an error with the service
        occurs
        """
        pass

    def get_attr_from_bag(self, name):
        """
        Look up an attribute associate with the service.  We can probably
        use __getattr__ instead, but i wanted to make it explicit in the 
        API definition.
        """
        pass



