#Cookbook Name: user

user node[:username] do
    comment "Dynamically created user."
    gid "#{node[:groupname]}"
    home "/home/#{node[:username]}"
    shell "/bin/bash"
    supports :manage_home => true
end
