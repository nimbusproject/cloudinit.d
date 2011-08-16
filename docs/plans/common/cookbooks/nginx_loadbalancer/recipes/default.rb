template "/etc/nginx/nginx.conf" do
  source "nginx.erb"
  mode 0440
  owner "root"
  group "root"
  variables(
    :host1 => node[:host1],
    :host2 => node[:host2],
    :my_hostname => node[:my_hostname]
  )
end
service "nginx" do
  supports :status => true, :restart => true, :reload => true
  action [ :enable, :restart ]
end

