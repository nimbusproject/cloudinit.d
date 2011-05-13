#/bin/bash

if [ "X" == "X$CLOUDINITD_IAAS_ACCESS_KEY" ]; then
    echo "The env CLOUDINITD_IAAS_ACCESS_KEY must be set"
    echo "One of the tests will fail without this"
fi

if [ "X" == "X$CLOUDINITD_IAAS_SECRET_KEY" ]; then
    echo "The env CLOUDINITD_IAAS_SECRET_KEY must be set"
    echo "One of the tests will fail without this"
fi

source_dir=`dirname $0`
cd $source_dir
source_dir=`pwd`

export CLOUDINITD_TEST_PLAN_DIR="$source_dir/plans"
export PYTHONPATH=$source_dir/../
export CLOUDINITD_TESTENV=1
export CLOUD_BOOT_FAB=$source_dir/fakefab.sh
export CLOUD_BOOT_SSH=/bin/true


cd nosetests
nosetests --cover-package=cloudboot --with-coverage "${@}"
