require 'resolv'

mysql_pass = node[:mysql][:password]
postgres_pass = node[:postgres][:password]
basedir = node[:filesystem][:basedir]
username = node[:username]
api_host = node[:api_host]
controller_host = node[:controller_host]
controller_ip = Resolv.new.getaddress(controller_host)
vcap_home = "/home/#{username}/cloudfoundry/vcap"
to_start = node[:services]

packages = [
    'coreutils',
    'autoconf',
    'curl',
    'git-core',
    'ruby',
    'bison',
    'build-essential',
    'zlib1g-dev',
    'libssl-dev',
    'libreadline5-dev'
  ]

case node[:platform]
  when "debian","ubuntu"
    packages.each do |pkg|
      package pkg do
        action :install
    end
  end
end

# rvm should come from a different recipe
 remote_file "/tmp/install_rvm" do
    source "https://rvm.beginrescueend.com/install/rvm"
    mode "0755"
 end

 execute "Installing rvm" do
  user "#{username}"
  group "ubuntu"
  action :run
  command "/tmp/install_rvm"
  creates "/home/#{username}/.rvm"
  environment ({'HOME' => "/home/#{username}"})
 end

 script "configure bash" do
     interpreter "bash"
     user "#{username}"
     group "ubuntu"
     cwd "/tmp"
     environment ({'HOME' => "/home/#{username}"})
     code <<-EOH

echo '[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm"' > $HOME/.bashrc
export rvm_trust_rvmrcs_flag=1 >> $HOME/.bashrc

echo '[[ -f /home/cf/.bashrc ]] && . /home/cf/.bashrc' > $HOME/.bash_profile
     EOH
 end

 script "Installing gems" do
     interpreter "bash"
     user "#{username}"
     group "ubuntu"
     cwd "/tmp"
     environment ({'HOME' => "/home/#{username}"})
     not_if "test -e /home/#{username}/.rvm/gems/ruby-1.9.2-p180/bin/vmc"
     code <<-EOH
echo "Activate rvm"
rvm_path="$HOME/.rvm"
[[ -s "$rvm_path/scripts/rvm" ]] && source "$rvm_path/scripts/rvm"
type rvm | head -1

# remove rake from default and global gems and instead install manually
rm $HOME/.rvm/gemsets/default.gems
rm $HOME/.rvm/gemsets/global.gems

echo "Installing various rubies"
rvm install 1.9.2-p180
if [ $? -ne 0 ]; then
  echo "failed to rvm install 1.9.2-p180"
    exit 1
fi
rvm --default 1.9.2-p180
if [ $? -ne 0 ]; then
  echo "failed to rvm --default 1.9.2-p180"
    exit 1
fi
rvm install 1.8.7
if [ $? -ne 0 ]; then
  echo "failed to rvm install 1.8.7"
    exit 1
fi

# install only rake 0.8.7
rvm use 1.8.7
if [ $? -ne 0 ]; then
  echo "failed to rvm use 1.8.7"
    exit 1
fi
gem install rake --version '0.8.7' --no-rdoc --no-ri
if [ $? -ne 0 ]; then
  echo "failed to gem install rake --version '0.8.7' --no-rdoc --no-ri"
    exit 1
fi

rvm use 1.9.2-p180
if [ $? -ne 0 ]; then
      echo "failed to rvm use 1.9.2"
    exit 1
fi
gem install rake --version '0.8.7' --no-rdoc --no-ri
if [ $? -ne 0 ]; then
  echo "failed to gem install rake --version '0.8.7' --no-rdoc --no-ri"
    exit 1
fi
gem install vmc --no-rdoc --no-ri
if [ $? -ne 0 ]; then
  echo "failed to gem install vmc --no-rdoc --no-ri"
    exit 1
fi

exit 0

     EOH
 end

directory "/home/#{username}/cloudfoundry" do
  owner "#{username}"
  group "ubuntu"
  mode "0755"
  action :create
end

execute "Getting CF from git" do
    user "#{username}"
    group "ubuntu"
    action :run
    command "git clone https://github.com/cloudfoundry/vcap.git"
    creates "/home/#{username}/cloudfoundry/vcap"
    cwd "/home/#{username}/cloudfoundry"
end

execute "Update git" do
    user "#{username}"
    group "ubuntu"
    action :run
    command "git submodule update --init"
    cwd "/home/#{username}/cloudfoundry/vcap"
end


execute "setup vcap" do
    user "root"
    action :run
    command "setup/vcap_setup -a -s -p \"#{mysql_pass}\" -q \"#{postgres_pass}\""
    cwd "/home/#{username}/cloudfoundry/vcap"
end

execute "setup mysql" do
    user "root"
    action :run
    command "sed -i.bkup -e \"s/pass: root/pass: #{mysql_pass}/\" mysql_node.yml
"
    cwd "/home/#{username}/cloudfoundry/vcap/services/mysql/config"
end

execute "setup postgres" do
    user "#{username}"
    action :run
    command "sed -i.bkup -e \"s/9.0/8.4/g\" postgresql_gateway.yml"
    cwd "/home/#{username}/cloudfoundry/vcap/services/postgresql/config"
end

execute "setup postgres 2" do
    user "#{username}"
    action :run
    command "sed -i.bkup -e \"s/user: vcap/user: postgres/\" -e \"s/pass: vcap/pass: #{postgres_pass}/\" postgresql_node.yml"
    cwd "/home/#{username}/cloudfoundry/vcap/services/postgresql/config"
end

execute "copy in nginx conf" do
    user "root"
    action :run
    command "cp setup/simple.nginx.conf /etc/nginx/nginx.conf"
    cwd "/home/#{username}/cloudfoundry/vcap/"
end

execute "restart nginx" do
    user "root"
    action :run
    command "/etc/init.d/nginx restart"
    cwd "/home/#{username}/cloudfoundry/vcap/"
end

 script "Installing rake on vcap" do
     interpreter "bash"
     user "#{username}"
     cwd "/home/#{username}/cloudfoundry/vcap"
     environment ({'HOME' => "/home/#{username}"})
     code <<-EOH
echo "Activate rvm"
rvm_path="$HOME/.rvm"
[[ -s "$rvm_path/scripts/rvm" ]] && source "$rvm_path/scripts/rvm"
type rvm | head -1

rvm use 1.9.2-p180
if [ $? -ne 0 ]; then
      echo "failed to rvm use 1.9.2"
    exit 1
fi

cd $HOME/cloudfoundry/vcap
gem install bundler --no-rdoc --no-ri
if [ $? -ne 0 ]; then
    echo "failed to gem install bundler --no-rdoc --no-ri"
    exit 1
fi

rake bundler:install
if [ $? -ne 0 ]; then
    echo "failed to rake bundler:install"
    exit 1
fi

exit 0

     EOH
 end

script "Setup /etc/hosts" do
  interpreter "bash"
  user "root"
  environment ({'IP' => controller_ip, 'API' => api_host})
  not_if "grep vcap /etc/hosts"
  code <<-EOH
  echo $IP $API >> /etc/hosts
  echo '#Add app hostnames here:' >> /etc/hosts
  echo "#\$IP testapp.vcap" >> /etc/hosts
  EOH
end

controller_conf = "#{vcap_home}/cloud_controller/config/cloud_controller.yml"
script "Setup cloud_controller" do
  interpreter "bash"
  user username
  environment ({'CONTROLLER' => controller_ip,
                'CONF' => controller_conf,
                'API' => api_host})
  not_if "grep #{controller_ip} #{controller_conf}"
  code <<-EOH
  sed -i "s|external_uri:.*|external_uri: $API|" $CONF
  sed -i "s|local_route:.*|local_route: $CONTROLLER|" $CONF
  sed -i "s|mbus:.*|mbus: nats://$CONTROLLER:4222/|" $CONF
  EOH
end

router_conf = "#{vcap_home}/router/config/router.yml"
script "Setup router" do
  interpreter "bash"
  user username
  environment ({'CONTROLLER' => controller_ip, 'CONF' => router_conf})
  not_if "grep #{controller_ip} #{router_conf}"
  code <<-EOH
  sed -i "s|mbus:.*|mbus: nats://$CONTROLLER:4222/|" $CONF
  EOH
end

health_manager_conf = "#{vcap_home}/health_manager/config/health_manager.yml"
script "Setup health_manager" do
  interpreter "bash"
  user username
  environment ({'CONTROLLER' => controller_ip, 'CONF' => health_manager_conf})
  not_if "grep #{controller_ip} #{health_manager_conf}"
  code <<-EOH
  sed -i "s|local_route:.*|local_route: $CONTROLLER|" $CONF
  sed -i "s|mbus:.*|mbus: nats://$CONTROLLER:4222/|" $CONF
  EOH
end

dea_conf = "#{vcap_home}/dea/config/dea.yml"
script "Setup dea" do
  interpreter "bash"
  user username
  environment ({'CONTROLLER' => controller_ip, 'CONF' => dea_conf})
  not_if "grep #{controller_ip} #{dea_conf}"
  code <<-EOH
  sed -i "s|local_route:.*|local_route: $CONTROLLER|" $CONF
  sed -i "s|mbus:.*|mbus: nats://$CONTROLLER:4222/|" $CONF
  EOH
end

script "Start vcap" do
  interpreter "bash"
  user "#{username}"
  cwd "/home/#{username}/cloudfoundry/vcap"
  environment ({'VCAP' => vcap_home, 'HOME' => "/home/#{username}",
                'SERVICES' => to_start})
  code <<-EOH
  echo "Activate rvm"
  rvm_path="$HOME/.rvm"
  [[ -s "$rvm_path/scripts/rvm" ]] && source "$rvm_path/scripts/rvm"
  type rvm | head -1

  rvm use 1.9.2-p180
  if [ $? -ne 0 ]; then
    echo "failed to rvm use 1.9.2"
    exit 1
  fi

  cd $VCAP
  bin/vcap start $SERVICES
  EOH
end
