#!/bin/bash

# directory containing this script and the chef cookbooks directory
COMMON_DIR_REL="`dirname $0`"
COMMON_DIR=`cd $COMMON_DIR_REL; pwd`
DIRNAME="readytests"
# move into this directory in order to make commands simpler
cd $COMMON_DIR

if [ ! -d "$DIRNAME" ]; then
  echo "error, packaging script cannot orient itself, no cookbooks directory?"
  exit 1
fi

if [ -f $DIRNAME.tar.gz ]; then
  rm $DIRNAME.tar.gz
  echo "Removed old $DIRNAME.tar.gz"
fi

tar czf $DIRNAME.tar.gz $DIRNAME
if [ $? -ne 0 ]; then
  echo "Failed to create $DIRNAME tarball"
  exit 1
fi

echo "Created $DIRNAME.tar.gz"
