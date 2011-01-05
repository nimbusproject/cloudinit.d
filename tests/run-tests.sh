#/bin/bash

if [ "X" == "X$AWS_ACCESS_KEY_ID" ]; then
    echo "The env AWS_ACCESS_KEY_ID must be set"
    exit 1
fi

if [ "X" == "X$AWS_SECRET_ACCESS_KEY" ]; then
    echo "The env AWS_SECRET_ACCESS_KEY must be set"
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
nosetests "${@}"
