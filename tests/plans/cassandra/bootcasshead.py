#!/usr/bin/env python

import sys
import os
import getpass
import tempfile
try:
    import simplejson as json
except:
    import json

f = open("bootconf.json", "r")
vals_dict = json.load(f)
f.close()
print vals_dict

print vals_dict['myip']
myip = vals_dict['myip']

os.putenv('DEBIAN_FRONTEND', 'noninteractive')
os.putenv('TERM', 'dumb')

commands = [
             "wget http://www.reverse.net/pub/apache//cassandra/0.6.13/apache-cassandra-0.6.13-bin.tar.gz",
             " tar -zxvf apache-cassandra-0.6.13-bin.tar.gz",
           ]

for cmd in commands:
    print cmd
    rc = os.system(cmd)
    if rc != 0:
        print "ERROR! %d" % (rc)
        sys.exit(rc)
seds = [
        ("<AutoBootstrap>false</AutoBootstrap>", "<AutoBootstrap>true</AutoBootstrap>"),
        ("<ListenAddress>localhost</ListenAddress>", "<ListenAddress>%s</ListenAddress>" % myip),
        ("<ThriftAddress>localhost</ThriftAddress>", "<ThriftAddress>%s</ThriftAddress>" % myip),
       ]


for (s, v) in seds:
    cmd = "sed -i 's^%s^%s^' apache-cassandra-0.6.13/conf/storage-conf.xml" % (s, v)
    rc = os.system(cmd)
    if rc != 0:
        print "ERROR! failed to sed in some values %d" % (rc)
        sys.exit(rc)


#  <Seeds>
#      <Seed>127.0.0.1</Seed>
#  </Seeds>


print "SUCCESS"
sys.exit(0)

