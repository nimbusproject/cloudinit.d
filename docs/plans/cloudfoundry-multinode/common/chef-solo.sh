#!/bin/bash

#set -e

. bootenv.sh

APP_NAME="Cloud Foundry"

COOKBOOK_GIT_URL="https://github.com/oldpatricka/vcap"
COOKBOOK_GIT_BRANCH="cloudinit-merge"
COOKBOOK_REPO_DIR="/var/vcap"
COOKBOOK_DIR="$COOKBOOK_REPO_DIR/dev_setup/cookbooks"
ROLES_DIR="$COOKBOOK_REPO_DIR/dev_setup/roles"
CHEF_LOGLEVEL="info"
MAKE_DIRS="/var/vcap.local"

function exit_on_error_with_error {
  is_error="$1"
  error_message="$2"

  if [ $is_error -ne 0 ]; then
    echo "$error_message"
    exit $is_error
  fi
}


CMDPREFIX=""
if [ `id -u` -ne 0 ]; then
  CMDPREFIX="sudo "
fi

# ========================================================================
# The run name can differentiate multiple chef runs on same base node
# ========================================================================

if [ "X" == "X$1" ]; then
  echo "argument required, the run name"
  exit 1
fi

RUN_NAME=$1

# ========================================================================
# Make needed shim directories
# ========================================================================

for directory in $MAKE_DIRS; do
    $CMDPREFIX mkdir -p $directory
    $CMDPREFIX chown -R $username $directory
done

# ========================================================================
# Install git and chef-solo if necessary
# ========================================================================

which git
if [ $? -ne 0 ]; then
  which apt-get
  exit_on_error_with_error $? "git is missing. If this were a Debian system we would install it."

  export DEBIAN_FRONTEND=noninteractive
  export TERM=dumb

  $CMDPREFIX apt-get update  -f -y --force-yes --quiet --yes
  $CMDPREFIX apt-get install  -f -y --force-yes --quiet --yes git-core
fi

which chef-solo
if [ $? -ne 0 ]; then
    
  which apt-get
  if [ $? -ne 0 ]; then
     echo "chef-solo is missing. If this were a Debian system we would install it."
     exit 1
  fi
    
  export DEBIAN_FRONTEND=noninteractive
  export TERM=dumb

  $CMDPREFIX apt-get update  -f -y --force-yes --quiet --yes
  $CMDPREFIX apt-get install  -f -y --force-yes --quiet --yes ruby ruby-dev libopenssl-ruby rdoc ri irb build-essential wget ssl-cert

  cd /tmp
  wget http://production.cf.rubygems.org/rubygems/rubygems-1.7.2.tgz
  tar zxf rubygems-1.7.2.tgz
  cd rubygems-1.7.2
  $CMDPREFIX ruby setup.rb --no-format-executable
  $CMDPREFIX gem install chef --no-rdoc --no-ri
  $CMDPREFIX gem install ohai --no-rdoc --no-ri
fi



# ========================================================================
# Copy in, or update cookbook from git
# ========================================================================

TOPDIR_ABS_REL="`dirname $0`/.."
TOPDIR_ABS=`cd $TOPDIR_ABS_REL; pwd`

if [ -d "$COOKBOOK_REPO_DIR/.git" ]; then

  (cd $COOKBOOK_REPO_DIR && $CMDPREFIX git fetch)
  exit_on_error_with_error $? "Couldn't fetch from git repo '$COOKBOOK_GIT_URL'"
else

  $CMDPREFIX mkdir -p $COOKBOOK_REPO_DIR
  exit_on_error_with_error $? "Couldn't make repo dir '$COOKBOOK_REPO_DIR'"

  $CMDPREFIX git clone $COOKBOOK_GIT_URL $COOKBOOK_REPO_DIR
  exit_on_error_with_error $? "Couldn't clone git repo '$COOKBOOK_GIT_URL'"

fi


(cd $COOKBOOK_REPO_DIR && $CMDPREFIX git checkout $COOKBOOK_GIT_BRANCH)
exit_on_error_with_error $? "Couldn't checkout '$COOKBOOK_GIT_BRANCH' branch"

(cd $COOKBOOK_REPO_DIR && $CMDPREFIX git pull)
exit_on_error_with_error $? "Couldn't pull '$COOKBOOK_GIT_URL'"

(cd $COOKBOOK_REPO_DIR && $CMDPREFIX git submodule update --init)
exit_on_error_with_error $? "Couldn't update submodules for '$COOKBOOK_GIT_URL'"

$CMDPREFIX chown -R $username $COOKBOOK_REPO_DIR
exit_on_error_with_error $? "Couldn't chown '$COOKBOOK_REPO_DIR'"

echo "Retrieved Chef Cookbook from '$COOKBOOK_GIT_URL'"

# Check for replicated run name
REPLICA_RUN=`(cd /tmp/nimbusready/ && ls -d $RUN_NAME*)`
if [ -n $REPLICA_RUN ]; then
    RUN_NAME=$REPLICA_RUN
fi

if [ ! -f $TOPDIR_ABS/$RUN_NAME/bootconf.json ]; then
  echo "Cannot find chefroles.json ($TOPDIR_ABS/$RUN_NAME/bootconf.json)"
  exit 1
fi





# ========================================================================
# Prepare chef-solo configuration files
# ========================================================================

$CMDPREFIX mkdir -p $COOKBOOK_DIR/run/$RUN_NAME

$CMDPREFIX mv $TOPDIR_ABS/$RUN_NAME/bootconf.json $COOKBOOK_DIR/run/$RUN_NAME/chefroles.json

cat >> chefconf.rb << EOF
log_level :info
Chef::Log::Formatter.show_time = false

cookbook_path '$COOKBOOK_DIR'
role_path '$ROLES_DIR'
file_store_path '$COOKBOOK_DIR/tmp'
file_cache_path '$COOKBOOK_DIR/tmp'

EOF

# Will figure out variables + here-doc later:
#echo "cookbook_path '$COOKBOOK_DIR'" >> chefconf.rb
#echo "file_store_path '$COOKBOOK_DIR/tmp'" >> chefconf.rb
#echo "file_cache_path '$COOKBOOK_DIR/tmp'" >> chefconf.rb

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
#workaround to ensure new password is picked up
echo "Kill nats"
ps aux | awk '/nats-server/ && !/awk/ {print $2}' | xargs $CMDPREFIX kill

echo "Start vcap"
. $vcap_profile
# Kill nats server in case there's a config change we want to take effect
$CMDPREFIX kill `ps aux | grep nats-server | grep -v grep |awk '{print $2}'`
$vcap_home/bin/vcap -c $vcap_config start $vcap_start
