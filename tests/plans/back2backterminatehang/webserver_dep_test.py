#!/usr/bin/env python

import simplejson as json
import urllib
import os
import sys


f = open("./bootconf.json", "r")
vals_dict = json.load(f)
f.close()
print vals_dict['message']
print vals_dict['webserver']

url = "http://%s/test.txt" % (vals_dict['webserver'])
print url
f = urllib.urlopen(url)
data = f.read().strip()
print data
if data != vals_dict['message']:
    print "messages doesnt match! |%s| != |%s|" % (data, vals_dict['message'])
    sys.exit(1)
sys.exit(0)
