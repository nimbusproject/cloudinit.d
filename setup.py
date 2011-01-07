#!/usr/bin/env python

__author__ = 'bresnaha'

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import sys
Version = "0.1"

if float("%d.%d" % sys.version_info[:2]) < 2.5:
    sys.stderr.write("Your Python version %d.%d.%d is not supported.\n" % sys.version_info[:3])
    sys.stderr.write("cloudboot requires Python 2.5 or newer.\n")
    sys.exit(1)

setup(name='cloudboot',
      version=Version,
      description='An Open Source bootstrap tool for services in the cloud.',
      author='Nimbus Development Team',
      author_email='workspace-user@globus.org',
      url='http://www.nimbusproject.org/',
      packages=[ 'cloudboot', 'cloudboot.cli' ],
       entry_points = {
        'console_scripts': [
            'cloud-boot = cloudboot.cli.boot:main',
        ]
      },

      long_description="""
This package can be considered the /etc/rc.d of the cloud!

This libary helps users bootstrap many dependent VMs in a cloud (or many clouds).  Services are associated with
virtual machine images in a cloud and then organized into levels.  Each level is booted in order.  Booting a level
means launching and configuring all of the VMs needed for each service in the level to run.  Once level 1 is
booted and ready to go, booting begins on level 2.
""",
      license="Apache2",
      install_requires = ["boto", "sqlalchemy", "fabric"],
     )
