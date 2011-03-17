__author__ = 'bresnaha'

import os
from fabric.api import env, run, put, sudo, cd, get
from cloudinitd.statics import *


def _iftar(filename):
    """Return base filename if filename ends with .tar.gz (and does not simply equal that suffix)
    Otherwise return None
    """
    if not filename:
        return None
    idx = filename.rfind('.tar.gz')
    if idx > 0:
        return filename[:idx]
    else:
        return None

def _tartask(directory, basename, tarball):
    """Expand the tarball, ensure it contains a directory with the basename.
    Ensure run.sh exists inside.
    Return path to the run.sh file.
    """
    with cd(directory):
        run("tar -xvzf %s" % tarball)
    tardir = os.path.join(directory, basename)
    try:
        run("test -d %s" % tardir)
    except:
        raise Exception("The tarball does not expand to a directory of the same name: %s" % tardir)
    destpgm = os.path.join(tardir, "run.sh")
    try:
        run("test -f %s" % destpgm)
    except:
        raise Exception("The tarball does contain a 'run.sh' file: %s" % tarball)

    # In case they forgot:
    run("chmod +x %s" % destpgm)
    
    return destpgm

def readypgm(pgm=None):
    env.warn_only = True
    run('mkdir %s' % REMOTE_WORKING_DIR)
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (REMOTE_WORKING_DIR, relpgm)
    put(pgm, destpgm, mode=0755)
    tarname = _iftar(relpgm)
    if tarname:
         destpgm = _tartask(REMOTE_WORKING_DIR, tarname, destpgm)
    env.warn_only = False
    with cd(REMOTE_WORKING_DIR):
        run(destpgm)

def bootpgm(pgm=None, conf=None, output=None):
    run('mkdir %s' % REMOTE_WORKING_DIR)
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (REMOTE_WORKING_DIR, relpgm)
    put(pgm, destpgm, mode=0755)
    tarname = _iftar(relpgm)
    if tarname:
        destpgm = _tartask(REMOTE_WORKING_DIR, tarname, destpgm)
    if conf:
        destconf = "%s/bootconf.json" % REMOTE_WORKING_DIR
        put(conf, destconf)
    with cd(REMOTE_WORKING_DIR):
        run(destpgm)
        try:
            fetch_conf(output=output)
        except:
            pass

def fetch_conf(output=None):
    remote_output = "%s/bootout.json" % (REMOTE_WORKING_DIR)
    get(remote_output, output) 
