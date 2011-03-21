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

sys.exit(0)
