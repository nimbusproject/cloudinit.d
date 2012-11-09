import shutil
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

def _tartask(directory, basename, tarball, run_pgm=run):
    """Expand the tarball, ensure it contains a directory with the basename.
    Ensure run.sh exists inside.
    Return path to the run.sh file.
    """
    with cd(directory):
        run_pgm("tar -xvzf %s" % tarball)
    tardir = os.path.join(directory, basename)
    try:
        run_pgm("test -d %s" % tardir)
    except:
        raise Exception("The tarball does not expand to a directory of the same name: %s" % tardir)
    destpgm = os.path.join(tardir, "run.sh")
    try:
        run_pgm("test -f %s" % destpgm)
    except:
        raise Exception("The tarball does contain a 'run.sh' file: %s" % tarball)

    # In case they forgot:
    run_pgm("chmod +x %s" % destpgm)

    return destpgm

def _make_ssh(pgm, args="", local_exe=None):

    if local_exe:
        cmd = "%s %s" % (pgm, args)
        return cmd

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

    cmd = "%s %s %s %s %s%s '%s %s'" % (sshexec, port, ssh_opts, key, user, env.host, pgm, args)

    return cmd


def readypgm(pgm=None, args=None, stagedir=None, local_exe=None):
    local_exe = str(local_exe).lower() == 'true'
    pgm_to_use = run
    put_pgm = put
    if local_exe:
        pgm_to_use = local
        put_pgm = shutil.copy

    args = urllib.unquote(args)
    env.warn_only = True
    pgm_to_use('mkdir -p %s' % stagedir)
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (stagedir, relpgm)

    if local_exe:
        os.chdir(stagedir)
        put_pgm(pgm, destpgm)
        os.chmod(destpgm, 0755)
    else:
        put_pgm(pgm, destpgm, mode=0755)

    tarname = _iftar(relpgm)
    if tarname:
         destpgm = _tartask(stagedir, tarname, destpgm)
    env.warn_only = False
    destpgm = destpgm + " " + args
    with cd(stagedir):
        pgm_to_use(destpgm)

def cleanup_dirs(stagedir=None, local_exe=None):
    cmd = _make_ssh("rm -rf %s" %(stagedir), local_exe=local_exe)
    local(cmd)


def bootpgm(pgm=None, args=None, conf=None, env_conf=None, output=None, stagedir=None, remotedir=None, local_exe=None):
    local_exe = str(local_exe).lower() == 'true'
    pgm_to_use = run
    put_pgm = put
    if local_exe:
        pgm_to_use = local
        put_pgm = shutil.copy

    args = urllib.unquote(args)
    pgm_to_use('mkdir %s;chmod 777 %s' % (remotedir, remotedir))
    pgm_to_use('mkdir -p %s' % stagedir)
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (stagedir, relpgm)
    if local_exe:
        os.chdir(stagedir)
        put_pgm(pgm, destpgm)
        os.chmod(destpgm, 0755)
    else:
        put_pgm(pgm, destpgm, mode=0755)
    tarname = _iftar(relpgm)
    if tarname:
        destpgm = _tartask(stagedir, tarname, destpgm, run_pgm=pgm_to_use)
    if conf and conf != "None":
        destconf = "%s/bootconf.json" % stagedir
        put_pgm(conf, destconf)
        os.remove(conf)
    if env_conf and env_conf != "None":
        destenv = "%s/bootenv.sh" % stagedir
        put_pgm(env_conf, destenv)
        os.remove(env_conf)
    destpgm = destpgm + " " + args

    local_cmd = _make_ssh("cd %s;%s" %(stagedir, destpgm), local_exe=local_exe)
    if local_cmd:
        local(local_cmd)

    with cd(stagedir):
        #run(destpgm)
        try:
            fetch_conf(output=output, stagedir=stagedir, local_exe=local_exe)
        except:
            pass

def fetch_conf(output=None, stagedir=None, local_exe=None):
    remote_output = "%s/bootout.json" % (stagedir)

    if local_exe:
        shutil.copy(remote_output, output)
    else:
        get(remote_output, output)
