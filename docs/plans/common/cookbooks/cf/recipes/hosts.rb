require 'resolv'

vcap_domain = node[:vcap_domain]
api_host = node[:api_host]
controller_host = node[:controller_host]
controller_ip = Resolv.new.getaddress(controller_host)


script "Setup /etc/hosts" do
  interpreter "bash"
  user "root"
  environment ({'IP' => controller_ip, 'API' => api_host, 'DOMAIN' => vcap_domain})
  not_if "grep $API /etc/hosts"
  code <<-EOH
  echo $IP $API >> /etc/hosts
  echo '#Add app hostnames here:' >> /etc/hosts
  echo "#\$IP testapp.$DOMAIN" >> /etc/hosts
  EOH
end
