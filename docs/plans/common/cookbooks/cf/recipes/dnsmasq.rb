require 'resolv'

vcap_domain = node[:vcap_domain]
controller_host = node[:controller_host]
controller_ip = Resolv.new.getaddress(controller_host)

package "dnsmasq" do
  action :install
end

script "Configure dnsmasq" do
  interpreter "bash"
  user "root"
  environment ({'DOMAIN' => vcap_domain, 'IP' => controller_ip})
  code <<-EOH

  echo "address=/$DOMAIN/$IP" >> /etc/dnsmasq.d/vcap
  echo "prepend domain-name-servers 127.0.0.1;" >> /etc/dhcp3/dhclient.conf
  EOH
end

service "dnsmasq" do
  action :restart
end

service "networking" do
  action :restart
end
