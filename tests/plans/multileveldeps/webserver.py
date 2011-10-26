#!/usr/bin/env python

import sys
import os
import tempfile
import getpass
import simplejson as json

f = open("bootconf.json", "r")
vals_dict = json.load(f)
f.close()

(osf, fname) = tempfile.mkstemp()
print vals_dict['message']
os.write(osf, vals_dict['message'])
os.close(osf)
sudo = ""
if getpass.getuser() != "root":
    sudo = "sudo"

commands = [
    "%s apt-get update" % (sudo),
    "%s apt-get -y install apache2" % (sudo),
    "%s cp %s /var/www/test.txt && %s chmod 644 /var/www/test.txt" % (sudo, fname, sudo)
  ]
for cmd in commands:
    print cmd
    rc = os.system(cmd)
    if rc != 0:
        sys.exit(rc)

out_vals = {}
out_vals = {'testpgm' : 'hello' }
output = open('bootout.json', "w")
json.dump(out_vals, output)
output.close()

sys.exit(rc)

