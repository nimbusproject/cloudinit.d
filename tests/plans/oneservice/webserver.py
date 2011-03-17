#!/usr/bin/env python

import sys
import os

f = open("bootconf.json", "r")
lines = f.readlines()
f.close()

print lines
sys.exit(0)
