import warnings
warnings.simplefilter('ignore')

import os
import datetime
import threading
import uuid
import boto
import logging
import boto.ec2
try:
    from libcloud.types import Provider
    from libcloud.providers import get_driver
    from libcloud.base import NodeImage, NodeAuthSSHKey
except ImportError:
    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver
    from libcloud.compute.base import NodeImage, NodeAuthSSHKey

if os.environ.get('CLOUDINITD_NO_LIBCLOUD_VERIFY_SSL_CERT'):
    import libcloud.security
    libcloud.security.VERIFY_SSL_CERT = False

from urlparse import urlparse
from datetime import timedelta

import boto.ec2
#warnings.simplefilter('default')

try:
    from boto.regioninfo import RegionInfo
except:
    from boto.ec2.regioninfo import RegionInfo
import cloudinitd
from cloudinitd.exceptions import ConfigException, IaaSException, APIUsageException



g_fake_instance_table = {}

g_lock = threading.Lock()

class IaaSTestCon(object):
    def __init__(self):
        pass

    def get_all_instances(self, instance_ids=None):
        global g_fake_instance_table

        if not instance_ids:
            return g_fake_instance_table.values()
        v = [g_fake_instance_table[id] for id in g_fake_instance_table.keys() if id in instance_ids]
        #for id in g_fake_instance_table.keys():
        #    print instance_ids
        #    if id in instance_ids:
        #        v.append(g_fake_instance_table[id])
        return v

    def run_instance(self):
        h = "localhost"
        return IaaSTestInstance(h)

    def find_instance(self, instance_id):
        global g_fake_instance_table

        try:
            return g_fake_instance_table[instance_id]
        except Exception, ex:
            raise IaaSException(str(ex))


class IaaSBotoConn(object):
    def __init__(self, svc, key, secret, iaasurl, iaas):
        self._svc = svc

        if not iaasurl:
            if not iaas:
                iaas = "us-east-1"
            region = boto.ec2.get_region(iaas, aws_access_key_id=key, aws_secret_access_key=secret)
            if not region:
                raise ConfigException("The 'iaas' configuration '%s' does not specify a valid boto EC2 region." % iaas)
            self._con =  boto.connect_ec2(key, secret, region=region, validate_certs=False)
        else:
            (scheme, iaashost, iaasport, iaaspath) = cloudinitd.parse_url(iaasurl)
            region = RegionInfo(endpoint=iaashost, name=iaas)

            secure = scheme == "https"

            if not iaasport:
                self._con =  boto.connect_ec2(key, secret, region=region, path=iaaspath, is_secure=secure, validate_certs=False)
            else:
                self._con =  boto.connect_ec2(key, secret, port=iaasport, region=region, path=iaaspath, is_secure=secure, validate_certs=False)
            self._con.host = iaashost

    def get_all_instances(self, instance_ids=None):
        global g_lock
        g_lock.acquire()
        try:
            l = []
            for r in self._con.get_all_instances(instance_ids):
                l = l + r.instances
            cb_l = [IaaSBotoInstance(i, self._con) for i in l]
            return cb_l
        finally:
            g_lock.release()

    def run_instance(self):
        global g_lock
        g_lock.acquire()
        try:
            x = self._run_instance()
        finally:
            g_lock.release()
        return x

    def _run_instance(self):
        if self._svc is None:
            raise ConfigException("You can only launch instances if a service is associated with the connection")
        image = self._svc.get_dep("image")
        instance_type = self._svc.get_dep("allocation")
        key_name = self._svc.get_dep("keyname")
        security_groupname = self._svc.get_dep("securitygroups")

        sec_group = None
        if security_groupname:
            try:
                sec_group_a  = self._con.get_all_security_groups(groupnames=[security_groupname,])
                if sec_group_a:
                    sec_group = sec_group_a
            except Exception, boto_ex:
                sec_group = None

        reservation = self._con.run_instances(image, instance_type=instance_type, key_name=key_name, security_groups=sec_group)
        instance = reservation.instances[0]
        return IaaSBotoInstance(instance, self._con)

    def find_instance(self, instance_id):
        global g_lock
        g_lock.acquire()
        try:
            x = self._find_instance(instance_id)
        finally:
            g_lock.release()
        return x

    def _find_instance(self, instance_id):

        reservation = self._con.get_all_instances(instance_ids=[instance_id,])
        if len(reservation) < 1:
            raise IaaSException(Exception("There is no instance %s" % (instance_id)))
        if len(reservation[0].instances) < 1:
            ex = IaaSException(Exception("There is no instance %s" % (instance_id)))
            raise ex
        instance = reservation[0].instances[0]
        i = IaaSBotoInstance(instance, self._con)
        return i

class IaaSLibCloudConn(object):

    def __init__(self, svc, key, secret, iaasurl, iaas):
        #cloudinitd.log(log, logging.INFO, "loading up a lobcloud driver %s" % (iaas))
        self._svc = svc

        self._provider_lookup = {
            "dummy" : Provider.DUMMY,
            "ec2" : Provider.EC2,
            "ec2_us_east": Provider.EC2_US_EAST,
            "ec2_eu": Provider.EC2_EU,
            "ec2_eu_west": Provider.EC2_EU_WEST,
            "rackspace": Provider.RACKSPACE,
            "slicehost": Provider.SLICEHOST,
            "gogrid": Provider.GOGRID,
            "vpsnet": Provider.VPSNET,
            "linode": Provider.LINODE,
            "vcloud": Provider.VCLOUD,
            "rmuhosting": Provider.RIMUHOSTING,
            "ec2_us_west": Provider.EC2_US_WEST,
            "voxel": Provider.VOXEL,
            "softlayer": Provider.SOFTLAYER,
            "eucalyptus": Provider.EUCALYPTUS,
            "ecp": Provider.ECP,
            "ibm": Provider.IBM,
            "opennebula": Provider.OPENNEBULA,
            "dreamhost": Provider.DREAMHOST,
            "elastichosts": Provider.ELASTICHOSTS,
            "elastichosts_uk1": Provider.ELASTICHOSTS_UK1,
            "elastichosts_uk2": Provider.ELASTICHOSTS_UK2,
            "elastichosts_us1": Provider.ELASTICHOSTS_US1,
            "ec2_ap_southeast": Provider.EC2_AP_SOUTHEAST,
            "rackspace_uk": Provider.RACKSPACE_UK,
            "brightbox": Provider.BRIGHTBOX,
            "cloudsigma": Provider.CLOUDSIGMA,
            "nimbus": Provider.NIMBUS,
            }


        if not iaas:
            raise ConfigException("the iaas type must be set")
        self._iaas = iaas.lower().strip()
        self._iaas = iaas.replace("libcloud-", "")

        if self._iaas.isdigit():
            provider = int(self._iaas)
        else:
            if self._iaas in self._provider_lookup:
                provider = self._provider_lookup[self._iaas]
            else:
                raise ConfigException("%s is not a known libcloud driver" % (self._iaas))

        if provider == Provider.NIMBUS and not iaasurl:
            raise ConfigException("You must provide an IAAS URL to the Nimbus libcloud driver")

        self._Driver = get_driver(provider)

        if iaasurl is not None:
            url = urlparse(iaasurl)
            host = url.hostname
            port = url.port

            self._con = self._Driver(key, secret, host=host, port=port)
        else:
            self._con = self._Driver(key, secret)

    def find_instance(self, instance_id):
        i_a = self.get_all_instances([instance_id,])
        return i_a[0]

    def get_all_instances(self, instance_ids=None):
        nodes = self._con.list_nodes()
        if instance_ids:
            nodes = [IaaSLibCloudInstance(self, n, self._Driver, self._con) for n in nodes if n.name in instance_ids]
        else:
            nodes = [IaaSLibCloudInstance(self, n, self._Driver, self._con) for n in nodes]
        return nodes

    def run_instance(self):
        if self._svc is None:
            raise ConfigException("You can only launch instances if a service is associated with the connection")

        image = self._svc.get_dep("image")
        instance_type = self._svc.get_dep("allocation")
        key_name = self._svc.get_dep("keyname")
        security_groupname = self._svc.get_dep("securitygroups")
        name = self._svc.name
        key_file = self._svc.get_dep("localkey")

        image = NodeImage(image, name, self._Driver)

        sizes = self._con.list_sizes()
        sz = None
        for s in sizes:
            if s.id == instance_type:
                sz = s
        if sz == None:
            raise Exception("The allocation size %s does not exist" % (instance_type))

        size = sz
        node_data = {
            'name':name,
            'size':size,
            'image':image,
        }

        if key_file:
            f = open(key_file, "r")
            pubkey = f.read()
            f.close()
            auth = NodeAuthSSHKey(pubkey)
            node_data['auth'] = auth

        if key_name:
            node_data['ex_keyname'] = key_name
        if security_groupname:
            node_data['ex_securitygroup'] = security_groupname
        node = self._con.create_node(**node_data)

        return IaaSLibCloudInstance(self, node, self._Driver, self._con)


class IaaSLibCloudInstance(object):

    def __init__(self, con, node, driver, libcloud_con):
        self._node = node
        self._con = con
        self._myid = node.get_uuid()
        self._Driver = driver
        self._libcloud_con = libcloud_con

    def terminate(self):
        self._node.destroy()

    def update(self):
        all_node = self._libcloud_con.list_nodes()

        for n in all_node:
            if n.get_uuid() == self._myid:
                self._node = n
                return

    def get_hostname(self):
        return self._node.public_ip[0]

    def get_state(self):
        return self._node.extra['status']

    def get_id(self):
        return self._node.id

    def cancel(self):
        pass



class IaaSTestInstance(object):

    def __init__(self, hostname, time_to_hostname=1.0):
        global g_fake_instance_table

        env_name = 'CLOUDINITD_CBIAAS_TEST_HOSTNAME_TIME'
        if env_name in os.environ:
            try:
                waittime = float(os.environ[env_name])
                time_to_hostname = waittime
            except Exception, ex:
                #cloudinitd.log(log, logging.WARN, "%s was set but not to a float. %s" % (env_name, str(ex)))
                pass

        self.public_dns_name = None
        self.state = "pending"

        if 'CLOUDINITD_TESTENV' in os.environ and os.environ['CLOUDINITD_TESTENV'] == "2":
            hostname = "DRY RUN"
        self._hostname = hostname
        self.id = str(uuid.uuid4()).split('-')[0]
        g_fake_instance_table[self.id] = self

        self.time_to_hostname = time_to_hostname
        self._time_next_state = datetime.datetime.now() + timedelta(days=0, seconds=time_to_hostname)
        self._next_state = "running"

    def cancel(self):
        pass

    def get_state(self):
        return self.state

    def terminate(self):
        self._time_next_state = datetime.datetime.now() + timedelta(days=0, seconds=self.time_to_hostname)
        self._next_state = "running"
        self.state = "shutting-down"

    def update(self):
        now = datetime.datetime.now()
        if self._time_next_state and self._next_state and now > self._time_next_state:
            self.state = self._next_state
            self.public_dns_name = self._hostname
            self._next_state = None
            self._time_next_state = None
        return self.state

    def get_hostname(self):
        return self.public_dns_name

    def get_id(self):
        return self.id

class IaaSBotoInstance(object):

    def __init__(self, instance, botocon):
        self._instance = instance
        self._lock = threading.Lock()
        self._botocon = botocon

    def terminate(self):
        self._lock.acquire()
        try:
            try:
                x = self._instance.terminate()
            except IndexError:
                raise
        finally:
            self._lock.release()
        return x

    def update(self):
        self._lock.acquire()
        try:
            x = self._instance.update()
        finally:
            self._lock.release()
        return x

    def get_hostname(self):
        self._lock.acquire()
        try:
            return self._instance.public_dns_name
        finally:
            self._lock.release()

    def get_state(self):
        self._lock.acquire()
        try:
            return self._instance.state
        finally:
            self._lock.release()

    def cancel(self):
        self._botocon.close()

    def get_id(self):
        self._lock.acquire()
        try:
            return self._instance.id
        finally:
            self._lock.release()


def iaas_get_con(svc, key=None, secret=None, iaasurl=None, iaas=None):
    # type check the port
    if 'CLOUDINITD_TESTENV' in os.environ:
        if secret == "fail":
            raise IaaSException("The test env is setup to fail here")
        return IaaSTestCon()

    if svc:
        if not key:
            key = svc.get_dep("iaas_key")
        if not secret:
            secret = svc.get_dep("iaas_secret")
        if not key:
            raise ConfigException("IaaS key %s not in provided" % (key))
        if not secret:
            raise ConfigException("IaaS secret %s not in provided" % (secret))
        if not iaasurl:
            iaasurl = svc.get_dep("iaas_url")
        if not iaas:
            iaas = svc.get_dep("iaas")

    # pick the connection driver
    ConDriver = IaaSBotoConn
    if iaas:
        ndx = iaas.find("libcloud-")
        if ndx == 0:
            ConDriver = IaaSLibCloudConn

    global g_lock

    g_lock.acquire()
    try:
    # can hindge the connection type on the iaas type
        con = ConDriver(svc, key, secret, iaasurl, iaas)
    finally:
        g_lock.release()
    return con

def _iaas_nimbus_validate(svc, log):
    rc = 0
    msg = None
    if svc._s.securitygroups:
        rc = 1
        msg = "The Nimbus IaaS platform does not support security groups as of 2.7"
        cloudinitd.log(log, logging.WARN, msg)

    return (rc, msg)

def _ec2_nimbus_validate(svc, log):
    return (0, None)


g_validate_funcs = {}
g_validate_funcs['nimbus'] = _iaas_nimbus_validate
g_validate_funcs['ec2'] = _ec2_nimbus_validate
g_validate_funcs['eucalyptus'] = _ec2_nimbus_validate

def iaas_validate(svc, log=logging):
    global g_validate_funcs
    iaas_type = svc._s.iaas

    if not iaas_type:
        iaas_type = "ec2"
    iaas_type = iaas_type.lower()
    if iaas_type not in g_validate_funcs.keys():
        iaas_type = "ec2"

    rc = 0
    msgs = []
    # make sure they have a local key if they are trying to ssh anywhere
    if not svc._s.localkey and 'SSH_AUTH_SOCK' not in os.environ:
        if svc._s.readypgm or svc._s.bootpgm:
            raise ConfigException("If you are using a readypgm or a bootpgm you must have an ssh key.  Either in the launch plan or via ssh forwarding")
        msgs.append("You have no localsshkeyname set for this plan.")
        rc = 1

    if not svc._s.username:
        if svc._s.readypgm or svc._s.bootpgm:
            msgs.append("You have no username set for ssh access.  This could be an oversite in the plan.")
            rc = 1

    iaas_type = iaas_type.lower()
    try:
        func = g_validate_funcs[iaas_type]
    except Exception, ex:
        raise APIUsageException("iaas type %s has a problem: %s" % (iaas_type, str(ex)))
    (rc1, msg1) = func(svc, log)
    if rc1 > rc:
        rc = rc1
    if msg1:
        msgs.append(msg1)

    return (rc, str(msgs))


