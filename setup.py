#!/usr/bin/env pythonv
import os

__author__ = 'bresnaha'

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import sys
Version = "0.1"

if float("%d.%d" % sys.version_info[:2]) < 2.5:
    sys.stderr.write("Your Python version %d.%d.%d is not supported.\n" % sys.version_info[:3])
    sys.stderr.write("cloudinitd requires Python 2.5 or newer.\n")
    sys.exit(1)

#get test plan list
def plans_list_dirs(p):

    files = []
    l = os.listdir(p)
    for f in l:
        this_d = os.path.join(p, f)
        if os.path.isdir(this_d):
            sub_l = plans_list_dirs(this_d)
            files = files + sub_l
        else:
            files.append((p, [this_d,],))

    return files

basepath = os.path.dirname(__file__)
test_plans = plans_list_dirs(os.path.join(basepath, "tests/plans"))
print test_plans

setup(name='cloudinitd',
      version=Version,
      description='An Open Source bootstrap tool for services in the cloud.',
      author='Nimbus Development Team',
      author_email='workspace-user@globus.org',
      url='http://www.nimbusproject.org/',
      packages=[ 'cloudinitd', 'cloudinitd.cli', 'cloudinitd.nosetests' ],
       entry_points = {
        'console_scripts': [
            'cloudinitd = cloudinitd.cli.boot:main',
        ],

      },
      data_files=test_plans,
      long_description="""
This package can be considered the /etc/rc.d of the cloud!

This libary helps users bootstrap many dependent VMs in a cloud (or many clouds).  Services are associated with
virtual machine images in a cloud and then organized into levels.  Each level is booted in order.  Booting a level
means launching and configuring all of the VMs needed for each service in the level to run.  Once level 1 is
booted and ready to go, booting begins on level 2.
""",
      license="Apache2",
      install_requires = ["boto >= 1.9", "sqlalchemy >= 0.6", "fabric >= 0.9"],
     )
