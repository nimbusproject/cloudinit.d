__author__ = 'bresnaha'

import cloudboot
import os

dir = os.path.dirname(os.path.abspath(cloudboot.__file__))
dir = os.path.dirname(dir)
g_plans_dir = os.path.join(dir, "tests/plans/")

if 'CLOUDBOOT_IAAS_ACCESS_KEY' not in os.environ and 'CLOUDBOOT_IAAS_SECRET_KEY' not in os.environ:
    os.environ['CLOUDBOOT_TESTENV'] = "1"
    os.environ['CLOUD_BOOT_FAB'] = "/bin/true"
    os.environ['CLOUD_BOOT_SSH'] = "/bin/true"
    os.environ['CLOUDBOOT_IAAS_ACCESS_KEY'] = "NOTHING"
    os.environ['CLOUDBOOT_IAAS_SECRET_KEY'] = "NOTHING"


from cloudboot.nosetests.basic_tests import *
from cloudboot.nosetests.basic_unit_tests import *
from cloudboot.nosetests.instance_dies_tests import *
from cloudboot.nosetests.pollable_tests import *
from cloudboot.nosetests.service_unit_tests import *