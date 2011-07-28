#!/usr/bin/env python

import os
import sys

if 'Hello' != sys.argv[1]:
    print "messages doesnt match! |%s|" % (sys.argv[1])
    sys.exit(1)
sys.exit(0)
