#!/usr/bin/env python

import sys
import os
import simplejson as json

f = open("bootconf.json", "r")
vals_dict = json.load(f)
f.close()

print vals_dict['message']
cmd = "sudo echo %s > /var/www/test.txt" % (vals_dict['message'])
print cmd
rc = os.system(cmd)

out_vals = {}
out_vals = {'testpgm' : 'hello' }
output = open('bootout.json', "w")
json.dump(out_vals, output)
output.close()

sys.exit(rc)

