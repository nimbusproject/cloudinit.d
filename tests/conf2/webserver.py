#!/usr/bin/env python

import sys
import os
import simplejson as json

f = open("bootconf.json", "r")
vals_dict = json.load(f)
f.close()

print vals_dict['message']
cmd = "sudo echo %s > /var/www/test.txt"
print cmd
rc = os.system(cmd)
sys.exit(rc)
