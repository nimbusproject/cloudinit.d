#/bin/bash

if [ "X" == "X$CLOUDBOOT_IAAS_ACCESS_KEY" ]; then
    echo "The env CLOUDBOOT_IAAS_ACCESS_KEY must be set"
    exit 1
fi

if [ "X" == "X$CLOUDBOOT_IAAS_SECRET_KEY" ]; then
    echo "The env CLOUDBOOT_IAAS_SECRET_KEY must be set"
    exit 1
fi

source_dir=`dirname $0`
cd $source_dir
source_dir=`pwd`

export CLOUDBOOT_TEST_PLAN_DIR="$source_dir/plans"
export PYTHONPATH=$source_dir/../
export CLOUDBOOT_TESTENV=1
export CLOUD_BOOT_FAB=$source_dir/fakefab.sh


cd nosetests
nosetests --cover-package=cloudboot --with-coverage "${@}"
