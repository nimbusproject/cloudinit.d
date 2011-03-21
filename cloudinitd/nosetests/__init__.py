__author__ = 'bresnaha'

import cloudinitd
import os

dir = os.path.dirname(os.path.abspath(cloudinitd.__file__))
dir = os.path.dirname(dir)
g_plans_dir = os.path.join(dir, "tests/plans/")

if 'CLOUDBOOT_IAAS_ACCESS_KEY' not in os.environ and 'CLOUDBOOT_IAAS_SECRET_KEY' not in os.environ:
    os.environ['CLOUDBOOT_TESTENV'] = "1"
    os.environ['CLOUD_BOOT_FAB'] = "/bin/true"
    os.environ['CLOUD_BOOT_SSH'] = "/bin/true"
    os.environ['CLOUDBOOT_IAAS_ACCESS_KEY'] = "NOTHING"
    os.environ['CLOUDBOOT_IAAS_SECRET_KEY'] = "NOTHING"
    os.environ['CLOUDBOOT_IAAS_ACCESS_KEY'] = "notrealkey"
    os.environ['CLOUDBOOT_IAAS_SECRET_KEY'] = "notrealkey"
    os.environ['CLOUDBOOT_IAAS_HOSTNAME'] = "NOTHING"
    os.environ['CLOUDBOOT_IAAS_PORT'] = "8978"

    os.environ['CLOUDBOOT_IAAS_IMAGE'] = "NOTHING"
    os.environ['CLOUDBOOT_IAAS_TYPE'] = "NOTHING"
    os.environ['CLOUDBOOT_IAAS_ALLOCATION'] = "NOTHING"
    os.environ['CLOUDBOOT_IAAS_SSHKEYNAME'] ="NOTHING"
    os.environ['CLOUDBOOT_IAAS_SSHKEY'] = "/etc/group"
    os.environ['CLOUDBOOT_SSH_USERNAME'] = "NOTHING"


from cloudinitd.nosetests.service_tests import *
from cloudinitd.nosetests.basic_tests import *
from cloudinitd.nosetests.basic_unit_tests import *
from cloudinitd.nosetests.instance_dies_tests import *
from cloudinitd.nosetests.pollable_tests import *
from cloudinitd.nosetests.service_unit_tests import *
from cloudinitd.nosetests.cloudinitd_tests import *
from cloudinitd.nosetests.prelaunch_tests import *
from cloudinitd.nosetests.plan_tests import *
from cloudinitd.nosetests.outputjson_tests import *