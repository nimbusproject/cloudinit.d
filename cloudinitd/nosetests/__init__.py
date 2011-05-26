

import cloudinitd
import os

dir = os.path.dirname(os.path.abspath(cloudinitd.__file__))
dir = os.path.dirname(dir)
g_plans_dir = os.path.join(dir, "tests/plans/")

if 'CLOUDINITD_IAAS_ACCESS_KEY' not in os.environ and 'CLOUDINITD_IAAS_SECRET_KEY' not in os.environ:
    os.environ['CLOUDINITD_TESTENV'] = "1"
    os.environ['CLOUDINITD_FAB'] = "/bin/true"
    os.environ['CLOUDINITD_SSH'] = "/bin/true"
    os.environ['CLOUDINITD_IAAS_ACCESS_KEY'] = "NOTHING"
    os.environ['CLOUDINITD_IAAS_SECRET_KEY'] = "NOTHING"
    os.environ['CLOUDINITD_IAAS_ACCESS_KEY'] = "notrealkey"
    os.environ['CLOUDINITD_IAAS_SECRET_KEY'] = "notrealkey"
    os.environ['CLOUDINITD_IAAS_URL'] = "NOTHING"

    os.environ['CLOUDINITD_IAAS_IMAGE'] = "NOTHING"
    #os.environ['CLOUDINITD_IAAS_TYPE'] =
    os.environ['CLOUDINITD_IAAS_ALLOCATION'] = "NOTHING"
    os.environ['CLOUDINITD_IAAS_SSHKEYNAME'] ="NOTHING"
    os.environ['CLOUDINITD_IAAS_SSHKEY'] = "/etc/group"
    os.environ['CLOUDINITD_SSH_USERNAME'] = "NOTHING"


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
from cloudinitd.nosetests.validate_tests import *
from cloudinitd.nosetests.singlevm_tests import *
from cloudinitd.nosetests.badplan_cleanup_tests import *
