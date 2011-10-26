import urllib
import os
from fabric.api import env, run, put, cd, get, local
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

def _make_ssh(pgm, args=""):

    ssh_opts = "-A -n -T -o BatchMode=yes -o StrictHostKeyChecking=no -o PasswordAuthentication=no"
    try:
        if 'CLOUDINITD_SSH_OPTS' in os.environ:
            ssh_opts = os.environ['CLOUDINITD_SSH_OPTS']
    except:
        pass

    sshexec = "ssh"
    try:
        if os.environ['CLOUDINITD_SSH']:
            sshexec = os.environ['CLOUDINITD_SSH']
    except:
        pass

    args = urllib.unquote(args)
    user = ""
    if env.user:
        user = env.user + '@'
    port = ""
    if env.port:
        port = "-p " + env.port
    key = ""
    if env.key_filename and env.key_filename[0]:
        key = "-i " + env.key_filename[0]

    cmd = "%s %s %s %s %s%s %s %s" % (sshexec, port, ssh_opts, key, user, env.host, pgm, args)

    return cmd


def readypgm(pgm=None, args=None, stagedir=None):
    args = urllib.unquote(args)
    env.warn_only = True
    run('mkdir -p %s' % stagedir)
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (stagedir, relpgm)
    put(pgm, destpgm, mode=0755)
    tarname = _iftar(relpgm)
    if tarname:
         destpgm = _tartask(stagedir, tarname, destpgm)
    env.warn_only = False
    destpgm = destpgm + " " + args
    with cd(stagedir):
        run(destpgm)

def bootpgm(pgm=None, args=None, conf=None, env_conf=None, output=None, stagedir=None):
    args = urllib.unquote(args)
    run('mkdir %s;chmod 777 %s' % (REMOTE_WORKING_DIR, REMOTE_WORKING_DIR))
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
    if env_conf and env_conf != "None":
        destenv = "%s/bootenv.sh" % stagedir
        put(env_conf, destenv)
    destpgm = destpgm + " " + args

    local_cmd = _make_ssh("'cd %s;%s'" %(stagedir, destpgm))
    if local_cmd:
        local(local_cmd)

    with cd(stagedir):
        #run(destpgm)
        try:
            fetch_conf(output=output, stagedir=stagedir)
        except:
            pass

def fetch_conf(output=None, stagedir=None):
    remote_output = "%s/bootout.json" % (stagedir)
    get(remote_output, output) 
