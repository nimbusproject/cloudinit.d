require 'resolv'

username = node[:username]
api_host = node[:api_host]
controller_host = node[:controller_host]
controller_ip = Resolv.new.getaddress(controller_host)
vcap_home = "/home/#{username}/cloudfoundry/vcap"
vcap_services = node[:vcap_services]


controller_conf = "#{vcap_home}/cloud_controller/config/cloud_controller.yml"
script "Setup cloud_controller" do
  interpreter "bash"
  user username
  environment ({'CONTROLLER' => controller_ip,
                'CONF' => controller_conf,
                'API' => api_host})
  only_if {vcap_services.include? "cloud_controller"}
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
  only_if {vcap_services.include? "router"}
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
  only_if {vcap_services.include? "health_manager"}
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
  only_if {vcap_services.include? "dea"}
  not_if "grep #{controller_ip} #{dea_conf}"
  code <<-EOH
  sed -i "s|local_route:.*|local_route: $CONTROLLER|" $CONF
  sed -i "s|mbus:.*|mbus: nats://$CONTROLLER:4222/|" $CONF
  EOH
end


script "Start vcap" do
  interpreter "bash"
  user username
  cwd vcap_home
  environment ({'VCAP' => vcap_home, 'HOME' => "/home/#{username}",
                'SERVICES' => vcap_services})
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

