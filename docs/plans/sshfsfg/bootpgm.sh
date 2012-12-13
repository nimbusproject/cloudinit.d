#!/bin/bash

set -e
source bootenv.sh
apt-get update
apt-get install -y sshfs

mkdir -p $SSHFS_MOUNTDIR

sshfs -o StrictHostKeyChecking=no  $SSHFS_MOUNTUSER@$SSHFS_MOUNTHOST: $SSHFS_MOUNTDIR


exit 0
