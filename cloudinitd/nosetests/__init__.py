

import cloudinitd
import os

dir = os.path.dirname(os.path.abspath(cloudinitd.__file__))
dir = os.path.dirname(dir)
g_plans_dir = os.path.join(dir, "tests/plans/")

if 'CLOUDINITD_IAAS_ACCESS_KEY' not in os.environ and 'CLOUDINITD_IAAS_SECRET_KEY' not in os.environ:
    os.environ['CLOUDINITD_TESTENV'] = "1"
    os.environ['CLOUDINITD_FAB'] = cloudinitd.find_true()
    os.environ['CLOUDINITD_SSH'] = cloudinitd.find_true()
    os.environ['CLOUDINITD_IAAS_ACCESS_KEY'] = "NOTHING"
    os.environ['CLOUDINITD_IAAS_SECRET_KEY'] = "NOTHING"
    os.environ['CLOUDINITD_IAAS_ACCESS_KEY'] = "notrealkey"
    os.environ['CLOUDINITD_IAAS_SECRET_KEY'] = "notrealkey"
    os.environ['CLOUDINITD_IAAS_URL'] = "NOTHING"

    os.environ['CLOUDINITD_IAAS_IMAGE'] = "NOTHING"
    #os.environ['CLOUDINITD_IAAS_TYPE'] =
    os.environ['CLOUDINITD_IAAS_ALLOCATION'] = "NOTHING"
    os.environ['CLOUDINITD_IAAS_SSHKEYNAME'] = "NOTHING"

    # keep this one if it is set. for localhost tests.
    os.environ['CLOUDINITD_IAAS_SSHKEY'] = os.environ.get('CLOUDINITD_IAAS_SSHKEY', "/etc/group")
    os.environ['CLOUDINITD_SSH_USERNAME'] = "NOTHING"


def is_a_test():
    return 'CLOUDINITD_TESTENV' in os.environ and os.environ['CLOUDINITD_TESTENV'] == "1"
