from datetime import timedelta
import datetime
import uuid
import boto
import boto.ec2
from boto.provider import Provider
from libcloud.providers import get_driver

try:
    from boto.regioninfo import RegionInfo
except:
    from boto.ec2.regioninfo import RegionInfo
import os
import cloudinitd
from cloudinitd.exceptions import ConfigException, IaaSException

__author__ = 'bresnaha'

g_fake_instance_table = {}

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

    def run_instance(self, image, instance_type, key_name, security_groupname=None):
        h = "localhost"
        return IaaSTestInstance(h)

    def find_instance(self, instance_id):
        global g_fake_instance_table

        try:
            return g_fake_instance_table[instance_id]
        except Exception, ex:
            raise IaaSException(str(ex))


class IaaSBotoConn(object):
    def __init__(self, con):
        self._boto_con = con

    def get_all_instances(self, instance_ids=None):
        return self._boto_con.get_all_instances(instance_ids) 

    def run_instance(self, image, instance_type, key_name, security_groupname=None):
        sec_group = None
        if security_groupname:
             sec_group_a = self._boto_con.get_all_security_groups(groupnames=[security_groupname,])
             sec_group = sec_group_a[0]

        reservation = self._boto_con.run_instances(image, instance_type=instance_type, key_name=key_name, security_groups=sec_group)
        instance = reservation.instances[0]
        return IaaSBotoInstance(instance)

    def find_instance(self, instance_id):
        reservation = self._boto_con.get_all_instances(instance_ids=[instance_id,])
        if len(reservation) < 1:
            raise IaaSException(Exception("There is no instance %s" % (instance_id)))
        if len(reservation[0].instances) < 1:
            ex = IaaSException(Exception("There is no instance %s" % (instance_id)))
            raise ex
        instance = reservation[0].instances[0]
        i = IaaSBotoInstance(instance)
        return i


class IaaSLibCloudConn(object):
    def __init__(self, con):
        self._con = con

    def get_all_instances(self, instance_ids=None):
        nodes = conn.list_nodes()
        if instance_ids:
            nodes = [IaaSLibCloudInstance(n) for n in nodes if n.name in instance_ids]
        else:
            nodes = [IaaSLibCloudInstance(n) for n in nodes]
        return nodes
#        name	String with a name for this new node (required) (type: str )#
	#size	The size of resources allocated to this node. (required) (type: NodeSize )
	#image	OS Image to boot on node. (required) (type: NodeImage )
	#location	Which data center to create a node in. If empty, undefined behavoir will be selected. (optional) (type: NodeLocation )
	#auth	Initial authentication information for the node (optiona

    def run_instance(self, image, instance_type, key_name, security_groupname=None):
        pass

    def find_instance(self, instance_id):
        i_a = self.get_all_instances([instance_id,])
        return i_a[0]

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

    def terminate(self):
        return self._instance.terminate()

    def update(self):
        return self._instance.update()

    def get_hostname(self):
        return self._instance.public_dns_name

    def get_state(self):
        return self._instance.state

    def get_id(self):
        return self._instance.id


class IaaSLibCloudInstance(object):

    def __init__(self, node):
        self._node = node

    def terminate(self):
        pass

    def update(self):
        pass

    def get_hostname(self):
        pass

    def get_state(self):
        pass

    def get_id(self):
        pass


    def _create_node_data(self, spec, **kwargs):
        """Utility to get correct form of data to create a Node.
"""
        image = NodeImage(spec.image, spec.name, self.node_driver)
        sz = ec2.EC2_INSTANCE_TYPES[spec.size] #XXX generalize (for Nimbus, etc)
        size = NodeSize(sz['id'], sz['name'], sz['ram'], sz['disk'], sz['bandwidth'], sz['price'], self.node_driver)
        node_data = {
            'name':spec.name,
            'size':size,
            'image':image,
            'ex_mincount':str(spec.count),
            'ex_maxcount':str(spec.count),
            'ex_userdata':spec.userdata,
            'ex_keyname':spec.keyname,
        }

        node_data.update(kwargs)


def iaas_get_con(key, secret, iaashostname=None, iaasport=None, iaas="us-east-1"):
    if 'CLOUDBOOT_TESTENV' in os.environ:
        if secret == "fail":
            raise IaaSException("The test env is setup to fail here")
        return IaaSTestCon()
    else:
        return _real_iaas_get_con(key, secret, iaashostname, iaasport, iaas)


def _real_iaas_get_con(key, secret, iaashostname=None, iaasport=None, iaas=None):
    orig_key = key
    orig_secret = secret
    # look up key and secret in env if needed
    key = cloudinitd.get_env_val(key)
    secret = cloudinitd.get_env_val(secret)
    if not key:
        raise ConfigException("IaaS key %s not in env" % (orig_key))
    if not secret:
        raise ConfigException("IaaS key %s not in env" % (orig_secret))
    
    if not iaashostname:
        if not iaas:
            raise ConfigException("There is no 'iaas' or 'iaas_hostname' configuration, you need one of these. %s" % (iaas))
        region = boto.ec2.get_region(iaas, aws_access_key_id=key, aws_secret_access_key=secret)
        if not region:
            raise ConfigException("The 'iaas' configuration '%s' does not specify a valid boto EC2 region." % iaas)
        con =  boto.connect_ec2(key, secret, region=region)
    else:
        region = RegionInfo(iaashostname)
        if not iaasport:
            con =  boto.connect_ec2(key, secret, region=region)
        else:
            con =  boto.connect_ec2(key, secret, port=iaasport, region=region)

    return IaaSBotoConn(con)

def _libcloud_iaas_get_con(key, secret, iaas, iaashostname=None, iaasport=None):
    if iaas.lower() == "nimbus":
        conn = None
    else:
        Driver = get_driver(Provider.EC2) 
        conn = Driver(key, secret)
    return IaaSLibCloudConn(conn)
