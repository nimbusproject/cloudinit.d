#!/usr/bin/env python

import sys
import os
import tempfile
import getpass
import simplejson as json
import uuid

f = open("bootconf.json", "r")
vals_dict = json.load(f)
f.close()

rc = 0
if 'message' not in vals_dict.keys():
    rc = 1
print "boottwo %s" % (vals_dict['message'])

sys.exit(rc)
