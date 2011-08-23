#!/bin/bash

start_dir=`pwd`
cd `dirname $0`
set -e
source ../bootenv.sh


$vcap_home/bin/vcap -c $vcap_config restart $vcap_start

if [ "X$vcaptests" != "X" ]; then
    sudo -H -i -u $username `pwd`/vcap_tests.sh
fi
sudo  vcap_domain=$vcap_domain api_host=$api_host -H -i -u $username `pwd`/run_app.sh `pwd`
./cf_ready.sh

