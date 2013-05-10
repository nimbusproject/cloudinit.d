import os
from setuptools import setup, find_packages
import sys

__author__ = 'bresnaha'

Version = "1.3"

if sys.version_info[:2] < (2,5):
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

install_requires = [
        "boto >= 2.6",
        "sqlalchemy >= 0.7.6",
        "fabric == 1.3",
        "simplejson >= 2.1",
        "apache-libcloud == 0.11.1",
        "uuid",
        "PyCrypto >=2.1, <2.4"
        ]

tests_require = install_requires + [
        'mock',
        'nose',
        ]

setup(name='cloudinitd',
      version=Version,
      description='An Open Source bootstrap tool for services in the cloud.',
      author='Nimbus Development Team',
      author_email='nimbus@mcs.anl.gov',
      url='http://www.nimbusproject.org/',
      packages=[ 'cloudinitd', 'cloudinitd.cli', 'cloudinitd.nosetests', 'tests' ],
       entry_points = {
        'console_scripts': [
            'cloudinitd = cloudinitd.cli.boot:main',
        ],

      },
      include_package_data = True,
      data_files = test_plans,
      package_data = {},
      download_url ="http://www.nimbusproject.org/downloads/cloudinitd-%s.tar.gz" % (Version),
      keywords = "cloud boot tool initialize services",
      long_description="""
This package can be considered the /etc/rc.d of the cloud!

This libary helps users bootstrap many dependent VMs in a cloud (or many clouds).  Services are associated with
virtual machine images in a cloud and then organized into levels.  Each level is booted in order.  Booting a level
means launching and configuring all of the VMs needed for each service in the level to run.  Once level 1 is
booted and ready to go, booting begins on level 2.
""",
      license="Apache2",
      install_requires = install_requires,
      tests_require=tests_require,
      extras_require={
          'test': tests_require,
      },
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python',
          'Topic :: System :: Clustering',
          'Topic :: System :: Distributed Computing',
          ],
     )
