__author__ = 'bresnaha'

import os
import sys
from fabric.api import env, run, local, put, cd, hide, puts, sudo
from fabric.decorators import runs_once


def readypgm(pgm=None):
    readydir = '/tmp/nimbusready'
    run('mkdir %s' % (readydir))
    relpgm = os.path.basename(pgm)
    destpgm = "%s/%s" % (readydir, relpgm)
    put(pgm, destpgm)
    if relpgm.find('tar.gz') >= 0:
        run("tar -zvf %s" % (destpgm))
        destpgm = '%s/run.sh' % (readydir)
    sudo(destpgm)


# XXX TODO XXX
# this is a BS function for testing.  it must be removed before anything will work
# XXX TODO XXX
def bootstrap(rolesfile=None):
    put(rolesfile, '/tmp/roles')
# XXX TODO XXX

def bootstrap_later(rolesfile=None):
    update_dt_data()
    put_chef_data(rolesfile=rolesfile)
    run_chef_solo()

def bootstrap_cei(rolesfile=None):
    put_provisioner_secrets()
    bootstrap(rolesfile=rolesfile)

def put_provisioner_secrets():
    ensure_opt()
    nimbus_key = os.environ.get('NIMBUS_KEY')
    nimbus_secret = os.environ.get('NIMBUS_SECRET')
    if not nimbus_key or not nimbus_secret:
        print "ERROR.  Please export NIMBUS_KEY and NIMBUS_SECRET"
        sys.exit(1)

    ec2_key = os.environ.get('AWS_ACCESS_KEY_ID')
    ec2_secret = os.environ.get('AWS_SECRET_ACCESS_KEY')
    if not ec2_key or not ec2_secret:
        print "ERROR.  Please export AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
        sys.exit(1)
    run("sudo sh -c 'echo export NIMBUS_KEY=%s >> /opt/cei_environment'" % nimbus_key)
    run("sudo sh -c 'echo export AWS_ACCESS_KEY_ID=%s >> /opt/cei_environment'" % ec2_key)

    with hide('running'):
        run("sudo sh -c 'echo export NIMBUS_SECRET=%s >> /opt/cei_environment'" % nimbus_secret)
        run("sudo sh -c 'echo export AWS_SECRET_ACCESS_KEY=%s >> /opt/cei_environment'" % ec2_secret)

def update():
    with hide('stdout'):
        run("sudo apt-get -q update")

@runs_once
def ensure_opt():
    run("if [ ! -d /opt ]; then sudo mkdir /opt; fi")

def update_dt_data():
    ensure_opt()

    # Checkout the latest cookbooks:
    cloned = False
    try:
        # If this test fails, fall back to cloning
        run('test -d /opt/dt-data')
        puts("dt-data repo present", flush=True)
    except:
        with cd("/opt/"):
            run("sudo git clone http://github.com/nimbusproject/dt-data.git")
            cloned = True
            puts("new dt-data repo clone", flush=True)

    # Sanity check
    run('test -d /opt/dt-data')

    # In the future, this will need to set the repo to things besides HEAD
    with cd("/opt/dt-data"):
        if not cloned:
            # No need to fetch if the fallback clone method was used above
            run("sudo git fetch")
        run("sudo git reset --hard origin/HEAD")

def put_chef_data(rolesfile=None):
    # put the role and config files:
    put("chefconf.rb", "/tmp/")
    put(rolesfile or "chefroles.json", "/tmp/chefroles.json")
    run("sudo mkdir -p /opt/dt-data/run")
    run("sudo mv /tmp/chefconf.rb /tmp/chefroles.json /opt/dt-data/run/")

def run_chef_solo():
    run("sudo chef-solo -l debug -c /opt/dt-data/run/chefconf.rb -j /opt/dt-data/run/chefroles.json")
