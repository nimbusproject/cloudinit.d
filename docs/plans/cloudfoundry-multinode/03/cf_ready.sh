#!/bin/bash
#
# cloudfoundry_ready.sh - script to test the readyness of Cloud Foundry Services

source bootenv.sh

# List of services to test
SERVICES="router cloud_controller dea health_manager"
VCAP="/home/$username/cloudfoundry/vcap/bin/vcap"

if [ -n "$vcap_services" ]; then
    SERVICES="$vcap_services"
fi

for service in $SERVICES ; do
    sudo -H -i -u $username $VCAP status $service | grep RUNNING || exit 1
done

sudo -H -i -u $username $VCAP status
exit $?

