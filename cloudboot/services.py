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

    def __init__(self, log=logging):
        self.services = {}
        self._log = log
        self._multi_top = MultiLevelPollable(log=log)

    def add_level(self, lvl_list):
        self._multi_top.add_level(lvl_list)

    def start(self):
        self._multi_top.start()

    def get_services(self):
        return self.services.items()

    def cancel(self):
        self._multi_top.cancel()

    def poll(self, callback=None):
        return self._multi_top.poll(callback=callback)

    def new_service(self, s, db):

        if s.name in self.services.keys():
            raise Exception("A service by the name of %s is already know to this boot configuration.  Please check your config files and try another name" % (s.name))

        if s.image == None and s.hostname == None:
            raise Exception("You must have an image or a hostname or there will be no VM")
        if s.image !=None and s.hostname != None:
            raise Exception("Only specify hostname *OR* image")

        # form all the objects needed by the service
        hostname_poller = None
        if s.image:
            iaas_con = _get_connection(s.iaas_key, s.iaas_secret, s.iaas_hostname, s.iaas_port)
            reservation = iaas_con.run_instances(s.image, instance_type=s.allocation, key_name=s.keyname)
            instance = reservation.instances[0]
            hostname_poller = InstanceHostnamePollable(instance, self._log)

        fabexec = "fab"
        try:
            if os.environ['CLOUD_BOOT_FAB']:
                fabexec = os.environ['CLOUD_BOOT_FAB']
        except:
            pass
        fabexec = fabexec + " -f %s -D -u %s -i %s " % (bootfabtasks.__file__, s.username, s.keyname)

        svc = SVCContainer(db, s, self, fabexec, hostname_poller=hostname_poller, log=self._log)
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

    def __init__(self, db, s, top_level, fabexec, hostname_poller=None, log=logging):
        self._vmhostname = s.hostname
        self._hostname_poller = hostname_poller
        self._log = log
        self._attr_bag = {}
        self._myname = s.name
        self._pollables = None
        self._readypgm = s.readypgm
        self._fabexec = fabexec
        self._done = False
        self._s = s
        self.name = s.name
        self._db = db
        self._top_level = top_level

        self.starting_state = 1
        self.transition_state = 2
        self.complete_state = 3

        if not s.hostname and not hostname_poller:
            raise Exception("You must provide a hostname or a hostname poller")        

        for bao in s.attrs:
            self._attr_bag[bao.key] = bao.value

        self._bootconf = s.bootconf
        if s.bootconf:
            self._bootconf = self._fill_template(bootconf)
        self._db.db_commit()

    def __str__(self):
        return self.name

    def get_vm_instance(self):
        if self._hostname_poller:
            return self._hostname_poller.get_instance()
        return None

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
            raise Exception("The service %s has no attr by the name of %s.  Please check your config files" % (self._myname, key))

    def start(self):
        # load up deps.  This must be delayed until start is called to ensure that previous levels have the populated
        # values
        if self._s.deps and self._s.contextualized == 0:
            parser = ConfigParser.ConfigParser()
            parser.read(self._s.deps)
            keys_val = parser.items("deps")

            pattern = re.compile('\$\{(.*?)\.(.*)\}')
            for (ka,val) in keys_val:
                match = pattern.search(val)
                if match:
                    svc_name = match.group(1)
                    attr_name = match.group(2)
                    val = self._top_level.find_dep(svc_name, attr_name)
                bao = BagAttrsObject(ka, val)
                self._s.attrs.append(bao)

        if self._hostname_poller:
            self._hostname_poller.start()
        #self._execute_callback(self.starting_state, "starting the %s service." % (self._myname))


    def _execute_callback(self, callback, state, msg):
        if not callback:
            return
        callback(self, state, msg)

    def poll(self, callback=None):
        if self._done:
            return True
        # if we already have a hostname move onto polling the fab tasks
        if self._vmhostname and self._vmhostname != "":
            if not self._pollables:
                self._pollables = MultiLevelPollable(log=self._log)

                if self._bootconf:
                    cmd = self._get_boot_cmd()
                    _boot_poller = PopenExecutablePollable(cmd, log=self._log)
                    self._pollables.add_level([_boot_poller])

                if self._readypgm:
                    cmd = self._get_readypgm_cmd()
                    _ready_poller = PopenExecutablePollable(cmd, log=self._log)
                    self._pollables.add_level([_ready_poller])
                self._pollables.start()

            rc = self._pollables.poll(callback=callback)
            if rc:                
                self._done = True
                self._s.contextualized = 1
                self._db.db_commit()
                self._execute_callback(callback, self.complete_state, "Service Complete")
            return rc

        if self._hostname_poller.poll():
            self._vmhostname = self._hostname_poller.get_hostname()
            self._s.hostname = self._vmhostname
            self._db.db_commit()
            self._execute_callback(callback, self.transition_state, "Acquired the hostname: %s" %(self._vmhostname))
        return False

    def _get_readypgm_cmd(self):
        cmd = self._fabexec + " readypgm:hosts=%s,pgm=%s" % (self._vmhostname, self._readypgm)
        return cmd

    def _get_boot_cmd(self):
        if self._myname == "provisioner":
            boot = "bootstrap_cei"
        else:
            boot = "bootstrap"
        cmd = self._fabexec + " %s:hosts=%s,rolesfile=%s" % (boot, self._vmhostname, self._bootconf)
        return cmd

    def _fill_template(self, path):

        if not os.path.exists(path):
            raise Exception("template file does not exist: %s" % path)

        f = open(path)
        doc_tpl = f.read()
        f.close()

        template = string.Template(doc_tpl)
        try:
            document = template.substitute(self._attr_bag)
        except ValueError,e:
            raise Exception("The file '%s' has a variable that could not be found: %s" % (path, str(e)))

        # having the template name in the temp file name makes it easier
        # to identify
        prefix = os.path.basename(path)
        prefix += "_"

        (fd, newpath) = tempfile.mkstemp(prefix=prefix, text=True, dir=self.thisrundir)

        f = open(newpath, 'w')
        f.write(document)
        f.close()

        return newpath

    def cancel(self):
        return self._pollables.cancel()