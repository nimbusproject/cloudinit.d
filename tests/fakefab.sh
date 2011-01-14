#!/bin/bash 

rc=0
if [ "X" != "X$CLOUDBOOT_FAB_RC" ]; then
    rc=$CLOUDBOOT_FAB_RC
fi

slptim=1
if [ "X" != "X$CLOUDBOOT_FAB_SLEEP" ]; then
    slptim=$CLOUDBOOT_FAB_SLEEP
fi

sleep $slptim
exit $rc
