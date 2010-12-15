#!/usr/bin/env python

import urllib
import os

f = urllib.urlopen("http://localhost/test.txt")
data = f.read()
print data

f = open("/tmp/nimbusconf/bootconf.json", "r")
vals_dict = json.load(f)
f.close()

print vals_dict['message']

if data != vals_dict['message']:
    print "messages doesnt match!"
    sys.exit(1)
sys.exit(1)
