#!/bin/bash

source bootenv.sh
start_dir=`pwd`
cd `dirname $0`
set -e
if [ "X$vcaptests" != "X" ]; then
    sudo -H -i -u $username `pwd`/vcap_tests.sh
fi
sudo -H -i -u $username `pwd`/run_app.sh `pwd`
./cf_ready.sh

