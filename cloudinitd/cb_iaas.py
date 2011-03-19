from datetime import timedelta
import datetime
import threading
import uuid
import boto
import boto.ec2
##from boto.provider import Provider
#from libcloud.base import NodeImage, NodeSize
#from libcloud.providers import get_driver
#from libcloud.types import Provider

try:
    from boto.regioninfo import RegionInfo
except:
    from boto.ec2.regioninfo import RegionInfo
import os
import cloudinitd
from cloudinitd.exceptions import ConfigException, IaaSException

__author__ = 'bresnaha'

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
    def __init__(self, svc, key=None, secret=None, iaashostname=None, iaasport=None):
        iaas = None
        self._svc = svc
        if self._svc:
            key = svc.get_dep("iaas_key")
            secret = svc.get_dep("iaas_secret")
            if not key:
                raise ConfigException("IaaS key %s not in env" % (key))
            if not secret:
                raise ConfigException("IaaS key %s not in env" % (secret))

            iaashostname = svc.get_dep("iaas_hostname")
            iaasport = svc.get_dep("iaas_port")
            if iaasport:
                iaasport = int(iaasport)
            iaas = svc.get_dep("iaas")


        if not iaas:
            iaas = "us-east-1"

        if not iaashostname:
            region = boto.ec2.get_region(iaas, aws_access_key_id=key, aws_secret_access_key=secret)
            if not region:
                raise ConfigException("The 'iaas' configuration '%s' does not specify a valid boto EC2 region." % iaas)
            self._con =  boto.connect_ec2(key, secret, region=region)
        else:
            region = RegionInfo(iaashostname)
            if not iaasport:
                self._con =  boto.connect_ec2(key, secret, region=region)
            else:
                self._con =  boto.connect_ec2(key, secret, port=iaasport, region=region)
            self._con.host = iaashostname

    def get_all_instances(self, instance_ids=None):
        global g_lock
        g_lock.acquire()
        try:
            return self._con.get_all_instances(instance_ids)
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
        if self._svc == None:
            raise ConfigException("You can only launch instances if a service is associated with the connection")
        image = self._svc.get_dep("image")
        instance_type = self._svc.get_dep("allocation")
        key_name = self._svc.get_dep("keyname")
        security_groupname = self._svc.get_dep("securitygroups")

        sec_group = None
        if security_groupname:
             sec_group_a = self._con.get_all_security_groups(groupnames=[security_groupname,])
             if sec_group_a:
                 sec_group = sec_group_a[0]

        reservation = self._con.run_instances(image, instance_type=instance_type, key_name=key_name, security_groups=sec_group)
        instance = reservation.instances[0]
        return IaaSBotoInstance(instance)

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
        i = IaaSBotoInstance(instance)
        return i

#
#class IaaSLibCloudConn(object):
#    def __init__(self, svc, key=None, secret=None):
#
#        self._svc = svc
#        if self._svc:
#            key = svc.get_dep("iaas_key")
#            secret = svc.get_dep("iaas_secret")
#            if not key:
#                raise ConfigException("IaaS key %s not in env" % (key))
#            if not secret:
#                raise ConfigException("IaaS key %s not in env" % (secret))
#
#        Driver = get_driver(Provider.EC2)
#        self._con = Driver(key, secret)
#        self._driver = Driver
#
#    def get_all_instances(self, instance_ids=None):
#        nodes = self._con.list_nodes()
#        if instance_ids:
#            nodes = [IaaSLibCloudInstance(n) for n in nodes if n.name in instance_ids]
#        else:
#            nodes = [IaaSLibCloudInstance(n) for n in nodes]
#        return nodes
##        name	String with a name for this new node (required) (type: str )#
#	#size	The size of resources allocated to this node. (required) (type: NodeSize )
#	#image	OS Image to boot on node. (required) (type: NodeImage )
#	#location	Which data center to create a node in. If empty, undefined behavoir will be selected. (optional) (type: NodeLocation )
#	#auth	Initial authentication information for the node (optiona
#
#    #def run_instance(self, image, instance_type, key_name, security_groupname=None):
#
#    def run_instance(self):
#        if self._svc == None:
#            raise ConfigException("You can only launch instances if a service is associated with the connection")
#
#        image = self._svc.get_dep("image")
#        instance_type = self._svc.get_dep("allocation")
#        key_name = self._svc.get_dep("keyname")
#        security_groupname = self._svc.get_dep("securitygroups")
#        name = self._svc.name
#
#        image = NodeImage(image, name, self._driver)
#        sz = ec2.EC2_INSTANCE_TYPES[instance_type]
#        size = NodeSize(sz['id'], sz['name'], sz['ram'], sz['disk'], sz['bandwidth'], sz['price'], self._driver)
#        node_data = {
#            'name':name,
#            'size':size,
#            'image':image,
#            'ex_mincount':str(1),
#            'ex_maxcount':str(1),
#            'ex_securitygroup': security_groupname,
#            'ex_keyname':key_name,
#        }
#        node = driver.create_node(**node_data)
#        return IaaSLibCloudInstance(self, node)
#
#
#    def find_instance(self, instance_id):
#        i_a = self.get_all_instances([instance_id,])
#        return i_a[0]

class IaaSTestInstance(object):

    def __init__(self, hostname, time_to_hostname=2.0):
        global g_fake_instance_table

        self.public_dns_name = None
        self.state = "pending"
        
        self._hostname = hostname
        self.id = str(uuid.uuid4()).split('-')[0]
        g_fake_instance_table[self.id] = self

        self.time_to_hostname = time_to_hostname
        self._time_next_state = datetime.datetime.now() + timedelta(days=0, seconds=time_to_hostname)
        self._next_state = "running"

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

    def __init__(self, instance):
        self._instance = instance
        self._lock = threading.Lock()

    def terminate(self):
        self._lock.acquire()
        try:
            x = self._instance.terminate()
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

    def get_id(self):
        self._lock.acquire()
        try:
            return self._instance.id
        finally:
            self._lock.release()

#
#class IaaSLibCloudInstance(object):
#
#    def __init__(self, con, node):
#        self._node = node
#        self._con = con
#
#    def terminate(self):
#        self._node.destroy()
#
#    def update(self):
#        pass
#
#    def get_hostname(self):
#        pass
#
#    def get_state(self):
#        pass
#
#    def get_id(self):
#        pass



def iaas_get_con(svc, key=None, secret=None, iaashostname=None, iaasport=None):
    # type check the port
    if iaasport:
        iaasport = int(iaasport)
    
    if 'CLOUDBOOT_TESTENV' in os.environ:
        if secret == "fail":
            raise IaaSException("The test env is setup to fail here")
        return IaaSTestCon()
    else:
        global g_lock

        g_lock.acquire()
        try:
        # can hindge the connection type on the iaas type
            con = IaaSBotoConn(svc, key=key, secret=secret, iaashostname=iaashostname, iaasport=iaasport)
        finally:
            g_lock.release()
        return con
        

def _libcloud_iaas_get_con(key, secret, iaas, iaashostname=None, iaasport=None):
    if iaas.lower() == "nimbus":
        conn = None
    else:
        Driver = get_driver(Provider.EC2) 
        conn = Driver(key, secret)
    return IaaSLibCloudConn(conn, driver)
