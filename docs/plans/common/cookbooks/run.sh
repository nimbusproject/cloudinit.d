#!/bin/bash

#set -e

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
# Install chef-solo if necessary
# ========================================================================

which chef-solo
if [ $? -ne 0 ]; then
    
  which apt-get
  if [ $? -ne 0 ]; then
     echo "chef-solo is missing. If this were a Debian system we would install it."
     exit 1
  fi
    
  export DEBIAN_FRONTEND=noninteractive
  export TERM=dumb

  sudo apt-get update  -f -y --force-yes --quiet --yes
  sudo apt-get install  -f -y --force-yes --quiet --yes ruby ruby-dev libopenssl-ruby rdoc ri irb build-essential wget ssl-cert
 # sudo apt-get update
 # sudo apt-get install -y ruby-dev libopenssl-ruby rubygems
 # sudo gem install chef ohai --no-ri --no-rdoc --source http://gems.opscode.com --source http://gems.rubyforge.org
 # sudo ln -s /var/lib/gems/1.8/bin/chef-solo /usr/local/bin/
 # sudo ln -s /var/lib/gems/1.8/bin/ohai /usr/local/bin/
  

  cd /tmp
  wget http://production.cf.rubygems.org/rubygems/rubygems-1.7.2.tgz
  tar zxf rubygems-1.7.2.tgz
  cd rubygems-1.7.2
  sudo ruby setup.rb --no-format-executable
  sudo gem install chef --no-rdoc --no-ri
  sudo gem install ohai --no-rdoc --no-ri
  #sudo ln -s /var/lib/gems/1.8/bin/chef-solo /usr/local/bin/
  #sudo ln -s /var/lib/gems/1.8/bin/ohai /usr/local/bin/
  
fi


# ========================================================================
# Prepare chef-solo configuration files
# ========================================================================

CMDPREFIX=""
if [ `id -u` -ne 0 ]; then
  CMDPREFIX="sudo "
fi

$CMDPREFIX mkdir -p $COOKBOOK_DIR/run/$RUN_NAME

$CMDPREFIX mv $TOPDIR_ABS/bootconf.json $COOKBOOK_DIR/run/$RUN_NAME/chefroles.json

cat >> chefconf.rb << "EOF"
log_level :info
Chef::Log::Formatter.show_time = false

EOF

# Will figure out variables + here-doc later:
echo "cookbook_path '$COOKBOOK_DIR'" >> chefconf.rb
echo "file_store_path '$COOKBOOK_DIR/tmp'" >> chefconf.rb
echo "file_cache_path '$COOKBOOK_DIR/tmp'" >> chefconf.rb

$CMDPREFIX mv chefconf.rb $COOKBOOK_DIR/run/$RUN_NAME/chefconf.rb


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

$CMDPREFIX mv rerun-chef-$RUN_NAME.sh /opt/rerun-chef-$RUN_NAME.sh


# ========================================================================
# Run chef-solo launch script
# ========================================================================

echo "Running chef-solo"
$CMDPREFIX /opt/rerun-chef-$RUN_NAME.sh
