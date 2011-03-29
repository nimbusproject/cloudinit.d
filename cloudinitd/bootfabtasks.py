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

def readypgm(pgm=None, stagedir=None):
    env.warn_only = True
    run('mkdir -p %s' % stagedir)
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (stagedir, relpgm)
    put(pgm, destpgm, mode=0755)
    tarname = _iftar(relpgm)
    if tarname:
         destpgm = _tartask(stagedir, tarname, destpgm)
    env.warn_only = False
    with cd(stagedir):
        run(destpgm)

def bootpgm(pgm=None, conf=None, output=None, stagedir=None):
    run('mkdir -p %s' % stagedir)
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (stagedir, relpgm)
    put(pgm, destpgm, mode=0755)
    tarname = _iftar(relpgm)
    if tarname:
        destpgm = _tartask(stagedir, tarname, destpgm)
    if conf and conf != "None":
        destconf = "%s/bootconf.json" % stagedir
        put(conf, destconf)
    with cd(stagedir):
        run(destpgm)
        try:
            fetch_conf(output=output, stagedir=stagedir)
        except:
            pass

def fetch_conf(output=None, stagedir=None):
    remote_output = "%s/bootout.json" % (stagedir)
    get(remote_output, output) 
