#!/bin/bash 

rc=0
if [ "X" != "X$CLOUDINITD_FAB_RC" ]; then
    rc=$CLOUDINITD_FAB_RC
fi

slptim=1
if [ "X" != "X$CLOUDINITD_FAB_SLEEP" ]; then
    slptim=$CLOUDINITD_FAB_SLEEP
fi

sleep $slptim

exit $rc
