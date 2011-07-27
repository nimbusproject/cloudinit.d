#!/bin/bash

CHEF_LOGLEVEL="info"


# ========================================================================
# The run name can differentiate multiple chef runs on same base node
# ========================================================================

if [ "X" == "X$1" ]; then
  echo "argument required, the run name"
  exit 1
fi

RUN_NAME=$1


# ========================================================================
# Sanity checks on new VM instance
# ========================================================================

# run.sh is one level below the main tmp directory cloudinit.d sets up
TOPDIR_ABS_REL="`dirname $0`/.."
TOPDIR_ABS=`cd $TOPDIR_ABS_REL; pwd`
COOKBOOK_DIR=$TOPDIR_ABS/cookbooks

if [ ! -d $COOKBOOK_DIR ]; then
  echo "Cannot find cookbooks directory"
  exit 1
fi

if [ ! -f $TOPDIR_ABS/bootconf.json ]; then
  echo "Cannot find chefroles.json (bootconf.json)"
  exit 1
fi


# ========================================================================
# Prepare chef-solo configuration files
# ========================================================================

CMDPREFIX=""
if [ `id -u` -ne 0 ]; then
  CMDPREFIX="sudo "
fi

$CMDPREFIX mkdir -p $COOKBOOK_DIR/run/$RUN_NAME
if [ $? -ne 0 ]; then
  exit 1
fi

$CMDPREFIX mv $TOPDIR_ABS/bootconf.json $COOKBOOK_DIR/run/$RUN_NAME/chefroles.json
if [ $? -ne 0 ]; then
  exit 1
fi

cat >> chefconf.rb << "EOF"
log_level :info
Chef::Log::Formatter.show_time = false

EOF

# Will figure out variables + here-doc later:
echo "cookbook_path '$COOKBOOK_DIR'" >> chefconf.rb
echo "file_store_path '$COOKBOOK_DIR/tmp'" >> chefconf.rb
echo "file_cache_path '$COOKBOOK_DIR/tmp'" >> chefconf.rb

$CMDPREFIX mv chefconf.rb $COOKBOOK_DIR/run/$RUN_NAME/chefconf.rb
if [ $? -ne 0 ]; then
  exit 1
fi


# ========================================================================
# Prepare chef-solo launch script
# ========================================================================

cat >> rerun-chef-$RUN_NAME.sh << "EOF"
#!/bin/bash

set -e

EOF

# Will figure out variables + here-doc later:
echo "chef-solo -l $CHEF_LOGLEVEL -c $COOKBOOK_DIR/run/$RUN_NAME/chefconf.rb -j $COOKBOOK_DIR/run/$RUN_NAME/chefroles.json" >> rerun-chef-$RUN_NAME.sh

chmod +x rerun-chef-$RUN_NAME.sh
if [ $? -ne 0 ]; then
  exit 1
fi

$CMDPREFIX mv rerun-chef-$RUN_NAME.sh /opt/rerun-chef-$RUN_NAME.sh
if [ $? -ne 0 ]; then
  exit 1
fi


# ========================================================================
# Run chef-solo launch script
# ========================================================================

echo "Running chef-solo"
$CMDPREFIX /opt/rerun-chef-$RUN_NAME.sh
if [ $? -ne 0 ]; then
  exit 1
fi
