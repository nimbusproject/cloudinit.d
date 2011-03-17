#!/usr/bin/env python

import simplejson as json
import urllib
import os
import sys

f = urllib.urlopen("http://localhost/test.txt")
data = f.read().strip()
print data

f = open("./bootconf.json", "r")
vals_dict = json.load(f)
f.close()

print vals_dict['message']

if data != vals_dict['message']:
    print "messages doesnt match! |%s| != |%s|" % (data, vals_dict['message'])
    sys.exit(1)
sys.exit(0)
