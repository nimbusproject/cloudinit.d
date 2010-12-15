__author__ = 'bresnaha'

import os
import sys
from fabric.api import env, run, put, sudo

def alive():
    run("/bin/true")

def readypgm(pgm=None):
    readydir = '/tmp/nimbusready'
    env.warn_only = True
    run('mkdir %s' % (readydir))
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (readydir, relpgm)
    put(pgm, destpgm, mode=0755)
    if relpgm.find('tar.gz') >= 0:
        run("tar -zvf %s" % (destpgm))
        destpgm = '%s/run.sh' % (readydir)    
    cmd = "cd %s; %s" % (readydir, destpgm)
    env.warn_only = False
    sudo(cmd)

def bootpgm(pgm=None, conf=None):
    confdir = '/tmp/nimbusconf'
    run('mkdir %s' % (confdir))
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (confdir, relpgm)
    put(pgm, destpgm, mode=0755)
    if relpgm.find('tar.gz') >= 0:
        run("tar -zvf %s" % (destpgm))
        destpgm = '%s/run.sh' % (confdir)
    if conf:
        destconf = "%s/bootconf.json" % (confdir)
        put(conf, destconf)
    cmd = "cd %s; %s" % (confdir, destpgm)
    sudo(cmd)


