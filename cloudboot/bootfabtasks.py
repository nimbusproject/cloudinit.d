__author__ = 'bresnaha'

import os
import sys
from fabric.api import env, run, local, put, cd, hide, sudo
from fabric.decorators import runs_once

def alive():
    run("/bin/true")

def readypgm(pgm=None):
    readydir = '/tmp/nimbusready'
    run('mkdir %s' % (readydir))
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (readydir, relpgm)
    put(pgm, destpgm)
    if relpgm.find('tar.gz') >= 0:
        run("tar -zvf %s" % (destpgm))
        destpgm = '%s/run.sh' % (readydir)
    sudo("chmod 755 %s" % (destpgm))
    cmd = "cd %s; %s" % (readydir, destpgm)
    sudo(cmd)

def bootpgm(pgm=None, conf=None):
    confdir = '/tmp/nimbusconf'
    run('mkdir %s' % (confdir))
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (confdir, relpgm)
    put(pgm, destpgm)
    if relpgm.find('tar.gz') >= 0:
        run("tar -zvf %s" % (destpgm))
        destpgm = '%s/run.sh' % (confdir)
    if conf:
        destconf = "%s/bootconf.json" % (confdir)
        put(conf, destconf)
    sudo("chmod 755 %s" % (destpgm))
    cmd = "cd %s; %s" % (confdir, destpgm)
    sudo(cmd)


