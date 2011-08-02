
username = node[:username]

script "starting services" do
  interpreter "bash"
  user "#{username}"
  group "ubuntu"
  cwd "/home/#{username}/cloudfoundry/vcap/bin"
  environment ({'HOME' => "/home/#{username}"})
  code <<-EOH
  source $HOME/.bashrc
  ./vcap restart
  exit $?
  EOH
end
