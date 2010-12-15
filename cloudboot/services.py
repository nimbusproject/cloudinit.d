import re
import os
from pollables import *
import bootfabtasks
import boto
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.connection import EC2Connection
import tempfile
import string
from cloudboot.persistantance import BagAttrsObject
import ConfigParser
from cloudboot.exceptions import APIUsageException, ConfigException, ServiceException, MultilevelException
from cloudboot.statics import *
import cloudboot

__author__ = 'bresnaha'

def _get_connection(key, secret, iaashostname=None, iaasport=None):
    # see comments in validate()
    if not iaashostname:
        con = EC2Connection(key, secret)
    else:
        region = RegionInfo(iaashostname)
        if not iaasport:
            con =  boto.connect_ec2(key, secret, region=region)
        else:
            con =  boto.connect_ec2(key, secret, port=iaasport, region=region)
    return con


class BootTopLevel(object):
    """
    This class is the top level boot description. It holds the parent Multilevel boot object which contains a set
    of many pollables.  The object also contains a way to get variable information from every service created.
    A service cannot be created without this object.  This object holds a dictionary of all services which is
    used for querying dependencies
    """

    def __init__(self, level_callback=None, service_callback=None, log=logging):
        self.services = {}
        self._log = log
        self._multi_top = MultiLevelPollable(log=log, callback=level_callback)
        self._service_callback = service_callback

    def add_level(self, lvl_list):
        self._multi_top.add_level(lvl_list)

    def get_current_level(self):
        return self._multi_top.get_level()

    def start(self):
        self._multi_top.start()

    def get_services(self):
        return self.services.items()

    def cancel(self):
        self._multi_top.cancel()

    def poll(self):
        return self._multi_top.poll()

    def new_service(self, s, db):

        if s.name in self.services.keys():
            raise APIUsageException("A service by the name of %s is already know to this boot configuration.  Please check your config files and try another name" % (s.name))

        if s.image == None and s.hostname == None:
            raise APIUsageException("You must have an image or a hostname or there will be no VM")
        if s.image !=None and s.hostname != None:
            raise APIUsageException("Only specify hostname *OR* image")

        svc = SVCContainer(db, s, self, log=self._log, callback=self._service_callback)
        self.services[s.name] = svc
        return svc

    def find_dep(self, svc_name, attr):
        try:
            svc = self.services[svc_name]
        except:
            return None
        return svc.get_dep(attr)


class SVCContainer(object):
    """
    This object represents a service which is the leaf object in the boot tree.  This service is a special case pollable type
    that consists of up to 3 other pollable types  a level pollable is used to keep the other MultiLevelPollable moving in order
    """

    def __init__(self, db, s, top_level, log=logging, callback=None):
        self._vmhostname = s.hostname
        self._log = log
        self._attr_bag = {}
        self._myname = s.name
        self._pollables = None
        self._readypgm = s.readypgm
        self._done = False
        self._s = s
        self.name = s.name
        self._db = db
        self._top_level = top_level

        self._make_hostname_poller()
        self._callback = callback
       
        self._db.db_commit()
        self._bootconf = None

        self._ssh_poller = None
        self._ready_poller = None
        self._boot_poller = None


    def _make_hostname_poller(self):
          # form all the objects needed by the service
        if self._s.image and self._s.hostname:
            raise APIUsageException("You cannot specify both a hotname and an image.  Check your config file")

        if self._s.image:            
            iaas_con = _get_connection(self._s.iaas_key, self._s.iaas_secret, self._s.iaas_hostname, self._s.iaas_port)
            reservation = iaas_con.run_instances(self._s.image, instance_type=self._s.allocation, key_name=self._s.keyname)
            instance = reservation.instances[0]
            self._hostname_poller = InstanceHostnamePollable(instance, self._log)

    def _get_fab_command(self):
        fabexec = "fab"
        try:
            if os.environ['CLOUD_BOOT_FAB']:
                fabexec = os.environ['CLOUD_BOOT_FAB']
        except:
            pass
        fabfile = bootfabtasks.__file__.replace("pyc", "py")
        cmd = fabexec + " -f %s -D -u %s -i %s " % (fabfile, self._s.username, self._s.localkey)
        return cmd

    def __str__(self):
        return self.name

    def get_dep(self, key):
        # first parse through the known ones, then hit the attr bag
        if key == "hostname":
            return self._vmhostname
        elif key == "instance_id":
            if self._hostname_poller:
                inst = self._hostname_poller.get_instance()
                return inst.id
            return None
        try:
            return self._attr_bag[key]
        except:
            raise ConfigException("The service %s has no attr by the name of %s.  Please check your config files" % (self._myname, key))

    def start(self):
        # load up deps.  This must be delayed until start is called to ensure that previous levels have the populated
        # values

        pattern = re.compile('\$\{(.*?)\.(.*)\}')
        for bao in self._s.attrs:                        
            val = bao.value
            match = pattern.search(val)
            if match:
                svc_name = match.group(1)
                attr_name = match.group(2)
                val = self._top_level.find_dep(svc_name, attr_name)
            self._attr_bag[bao.key] = val

        if self._s.bootconf:
            self._bootconf = self._fill_template(self._s.bootconf)

        if self._hostname_poller:
            self._hostname_poller.start()
        self._execute_callback(cloudboot.callback_action_started, "Service Started")


    def _execute_callback(self, state, msg):
        if not self._callback:
            return
        self._callback(self, state, msg)

    def poll(self):
        try:
            return self._poll()
        except MultilevelException, multiex:
            if self._ssh_poller in multiex.pollable_list:
                msg = "Service %s error getting ssh access to %s" % (self._myname, self._vmhostname)
                stdout = self._ssh_poller.get_stdout()
                stderr = self._ssh_poller.get_stderr()
            elif self._boot_poller in multiex.pollable_list:
                msg = "Service %s error configuring for boot: %s" % (self._myname, self._vmhostname)
                stdout = self._boot_poller.get_stdout()
                stderr = self._boot_poller.get_stderr()
            elif self._ready_poller in multiex.pollable_list:
                msg = "Service %s error running ready program" % (self._myname, self._vmhostname)
                stdout = self._ready_poller.get_stdout()
                stderr = self._ready_poller.get_stderr()
            raise ServiceException(multiex, self, msg, stdout, stderr)
            
        except Exception, ex:
            cloudboot.log(self._log, logging.ERROR, "%s" %(str(ex)), traceback)
            self._s.last_error = str(ex)
            self._db.db_commit()
            raise ServiceException(ex, self)

    def context_cb(self, popen_poller, action, msg):
        if action == cloudboot.callback_action_transition:
            self._execute_callback(action, msg)

    def _poll(self):
        if self._done:
            return True
        # if we already have a hostname move onto polling the fab tasks
        if self._vmhostname and self._vmhostname != "":
            if not self._pollables:
                self._pollables = MultiLevelPollable(log=self._log)

                cmd = self._get_ssh_ready_cmd()
                self._ssh_poller = PopenExecutablePollable(cmd, log=self._log)
                self._pollables.add_level([self._ssh_poller])
                if self._s.bootconf:
                    cmd = self._get_boot_cmd()
                    self._boot_poller = PopenExecutablePollable(cmd, log=self._log, allowed_errors=1)
                    self._pollables.add_level([self._boot_poller])

                if self._readypgm:
                    cmd = self._get_readypgm_cmd()
                    self._ready_poller = PopenExecutablePollable(cmd, log=self._log, allowed_errors=1)
                    self._pollables.add_level([self._ready_poller])
                self._pollables.start()

            rc = self._pollables.poll()
            if rc:                
                self._done = True
                self._s.contextualized = 1
                self._db.db_commit()
                self._execute_callback(cloudboot.callback_action_complete, "Service Complete")
                cloudboot.log(self._log, logging.DEBUG, self._boot_poller.get_output())
            return rc

        if self._hostname_poller.poll():
            self._vmhostname = self._hostname_poller.get_hostname()
            self._execute_callback(cloudboot.callback_action_transition, "Have hostname %s" %(self._vmhostname))
            self._s.hostname = self._vmhostname
            self._db.db_commit()
        return False

    def _get_ssh_ready_cmd(self):
        cmd = self._get_fab_command() + " alive:hosts=%s" % (self._vmhostname)
        return cmd

    def _get_readypgm_cmd(self):
        cmd = self._get_fab_command() + " readypgm:hosts=%s,pgm=%s" % (self._vmhostname, self._s.readypgm)
        return cmd

    def _get_boot_cmd(self):
        cmd = self._get_fab_command() + " bootpgm:hosts=%s,pgm=%s,conf=%s" % (self._vmhostname, self._s.bootpgm, self._bootconf)
        return cmd

    def _fill_template(self, path):

        if not os.path.exists(path):
            raise ConfigException("template file does not exist: %s" % path)

        f = open(path)
        doc_tpl = f.read()
        f.close()

        template = string.Template(doc_tpl)
        try:
            document = template.substitute(self._attr_bag)
        except ValueError,e:
            raise ConfigException("The file '%s' has a variable that could not be found: %s" % (path, str(e)))

        # having the template name in the temp file name makes it easier
        # to identify
        prefix = os.path.basename(path)
        prefix += "_"

        (fd, newpath) = tempfile.mkstemp(prefix=prefix, text=True)

        f = open(newpath, 'w')
        f.write(document)
        f.close()

        return newpath

    def cancel(self):
        return self._pollables.cancel()