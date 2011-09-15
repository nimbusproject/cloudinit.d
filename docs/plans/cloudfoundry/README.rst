Cloud Foundry Launch Plan README
================================

Introduction
------------

Cloud Foundry is an open Platform-as-a-Service (PaaS) project. This launch plan
will allow you to set up either a simple single node installation, or a multi
DEA worker node installation.


Prerequisites
-------------

Ensure that you have cloudinit.d installed. See the `cloudinit.d documentation`_
for instructions.

Ensure that you have your IaaS credentials exported into your environment::

    $ export CLOUDINITD_IAAS_ACCESS_KEY=<EC2 access key>
    $ export CLOUDINITD_IAAS_SECRET_KEY=<EC2 secret key>
    $ export CLOUDINITD_IAAS_SSHKEY=<EC2 ssh key name>
    $ export CLOUDINITD_IAAS_SSHKEYNAME=<path to the matching ssh key>

Boot Cloud Foundry
------------------

Once you have your credentials set up, you need to build a tarball for both the
Chef cookbooks used to build your Cloud Foundry installation, and the
readytests used to verify that your service is running properly. This is
scripted, so change to your plans directory and run the following::

    $ cd plans
    $ ./common/prepare-tarball.sh
    Created cookbooks.tar.gz
    $ ./cloudfoundry/01/prepare-tarball.sh 
    Created readytests.tar.gz

If you later modify the Cloud Foundry cookbooks, or the readytests, you will
need to re-run these scripts before you re-deploy Cloud Foundry.

Now run cloudinit.d to boot a single node installation::

    $ cloudinitd boot -v -v -v cloudfoundry/main.conf -n cf-single
    Starting up run cf-single
        Started IaaS work for singlenode
    Starting the launch plan.
    Begin boot level 1...
        Started singlenode

Please be patient. The Cloud Foundry setup scripts can take about 30 minutes to
run on a standard EC2 VM. This is because the Cloud Foundry setup installs
numerous packages, builds two versions of Ruby, Erlang/OTP, and node.js, in
addition to installing Cloud Foundry itself.


Testing Installation
--------------------

To test your installation, you should log in to your Cloud Foundry VM, and
switch to the cf user. You can get the domain name of the VM from the cloudinit.d
output (These instructions are based on the ones from the [Cloud Foundry README])::

    $ ssh ubuntu@ec2-0-0-0-0.compute-1.amazonaws.com
    [on vm]
    $ sudo su - cf
    [now cf user]

Test that we can connect to the Cloud Foundry service with the pre-defined
vcap.me address::

    $ vmc target api.vcap.me
    $ vmc info

Now we will register and login with our new account::

    $ vmc register --email cfuser@bar.com --passwd password
    $ vmc login --email cfuser@bar.com --passwd password

Run a Hello World app::

    $ mkdir hello && cd hello

Paste the following into hello.rb::

    require 'rubygems'
    require 'sinatra'

    get '/' do
      host = ENV['VMC_APP_HOST']
      port = ENV['VMC_APP_PORT']
      "<h1>XXXXX Hello from the Cloud! via: #{host}:#{port}</h1>"
    end

And now push the app to Cloud Foundry, and test it out::

    $ vmc push hello --instances 4 --mem 64M --url hello.vcap.me -n
    $ curl http://hello.vcap.me
    <h1>XXXXX Hello from the Cloud! via: 0.0.0.0:00000</h1>

It worked! 


Teardown
--------

Why don't we tear down our Cloud Foundry install now that we know that it
works. To do this, run the following::

    $ cloudinitd terminate cf-single
    Terminating cf-single
    SUCCESS level 1
    deleting the db file /Users/patricka/.cloudinitd/cloudinitd-cf-single.db


What now? A Multiple Node Launch
--------------------------------

Now that you've seen that cloudinitd can start a single Cloud Foundry node, you
could try the cloudfoundry-multinode plan, and boot a multiple node
installation. 

To do this, follow the same steps from the Boot Cloud Foundry section, but change
cloudfoundry to cloudfoundry-multi, like so::

    $ cloudinitd boot -v -v -v cloudfoundry-multi/main.conf -n cf-multi

This launch plan starts four DEA nodes, as well as one controller node that
runs all of the other Cloud Foundry services. For this to work, these DEA nodes
need to connect to the nats service running on the controller node.

In a manual deployment, we would first start the nats server, then manually
edit the dea.yml configuration file to point to it. We are going to start 4 DEA
nodes in this example, so you would otherwise need to manually set this option
four times. This is exactly the kind of situation where cloudinit.d is useful.
Instead of configuring this 4 times, we simply set a variable in our
cloudinit.d configuration file that points to our controller node, and
cloudinit.d feeds this information to Chef when it sets up the node.

Let's look at how this launch plan works. First note that our main cloudinit.d
configuration file has three boot levels. The first level starts everything but
the DEA service, and is otherwise the same as the single level in the single
node example above. The second level is more interesting. The file
02/level2.conf file defines the scaffolding for our DEA nodes. Let's take a
look::

    [svc-dea]
    bootconf: dea.json
    bootpgm: ../common/chef-solo.sh
    deps: deps.conf
    replica_count: 4
    # burned image
    image: ami-b769a9de
    # unix account name:
    bootpgm_args: dea
    readypgm: ../common/cf_ready.sh

This file points to the bootconf file for our DEA service (a Chef configuration script), the boot program (a Chef bootstrap script), and the dependencies for that configuration file. Also note the replica_count option, which means cloudinit.d will start 4 copies of the DEA.

Next look at the beginning of the deps.conf file. It is used to set up variablesfor the JSON file that is fed to Chef::

    [deps]
    controller_host: ${controller.hostname}
    base_username: ubuntu
    deployment_name: dea
    ...
    nats_pw: ${controller.nats_pw}

Take a look at how we set the controller_host variable. The ${controller.hostname} string is replaced with the full hostname of the controller node started in level 1. We can see how this is used in the Chef configuration file, dea.json::
  
    {
      "username": "${base_username}",
      ...
      "nats_server": {
          "user": "nats",
          "password": "${nats_pw}",
          "host": "${controller_host}",
          "port": "4222"
      },
      ...
    }

You should note that the nats password also comes from the controller. This configuration is used to automatically connect our booted DEA nodes with our controller node.

This JSON file is fed to the Cloud Foundry Chef recipe, and will produce a configuration string like in the DEA's configuration file::

    mbus: nats://nats:ham@ec2-184-73-108-198.compute-1.amazonaws.com:4222/

Once the DEA service starts up, it reads this configuration value, and
automatically connects to the nats service and becomes available to run apps in
your deployment.

Now that we've seen how cloudinit.d can start multiple nodes that depend on one another, let's try adding a new node by moving the MySQL service to its own node. 

Adding a MySQL node
===================

To add a new MySQL node to our setup, lets start by disabling the MySQL service
on our controller node. To do this, open up 01/controller.json, and remove
mysql and mysql_gateway from the list of recipes to install. The recipes line
should look like this now::

    "recipes":["role[cloudfoundry]", "role[nats_server]", "role[ccdb]", "role[router]", "role[cloud_controller]", "role[health_manager]", "role[redis]", "role[redis_gateway]", "role[mongodb]", "role[mongodb_gateway]"]

This will ensure that the MySQL chef recipes don't get run unnecessarily on
your controller node. To make sure MySQL isn't started on your controller,
you'll need to remove MySQL from the list of services to start. To do this,
open up deps.conf, and remove "mysql" from the vcap_start line. It should now
look like this::

    vcap_start: router cloud_controller health_manager mongodb redis

Now that MySQL is disabled on the controller, we can set it up as a new service
in level 2. To do this, open up 02/level2.conf, and add a MySQL service after
the DEA service::

    [svc-mysql]
    bootconf: mysql.json
    bootpgm: ../common/chef-solo.sh
    replica_count: 2
    deps: deps.conf
    #unix account name:
    bootpgm_args: mysql
    readypgm: ../common/cf_ready.sh

Pretty simple. Now create a mysql.json bootconf file, with the following contents::

    {
      "username": "${base_username}",
      "vcap_profile": "${vcap_profile}",
      "vcap_home": "${vcap_home}",
      "vcap_config": "${deployment_config}",
      "deployment":{
          "name": "${deployment_name}",
          "home": "${deployment_home}",
          "config_path": "${deployment_config}",
          "user": "${base_username}",
          "group": "ubuntu",
          "profile": "${vcap_profile}"
      },
      "cloudfoundry": {
          "revision": "HEAD",
          "path": "${vcap_home}"
      },
      "mysql": {
          "server_root_password": "${mysql_pw}",
          "server_repl_password": "${mysql_pw}"
      },
      "nats_server": {
          "user": "nats",
          "password": "${nats_pw}",
          "host": "${controller_host}",
          "port": "4222"
      },
      "vcap_start": "mysql",
      "recipes":["role[mysql]"]
    }

It's only differs from the DEA json config file by a few lines::

    17a18,21
    >   "mysql": {
    >       "server_root_password": "${mysql_pw}",
    >       "server_repl_password": "${mysql_pw}"
    >   },
    24,28c28,29
    <   "dea": {
    <       "local_route": ""
    <   },
    <   "vcap_start": "dea",
    <   "recipes":["role[dea]"]
    ---
    >   "vcap_start": "mysql",
    >   "recipes":["role[mysql]"]

Now we should be able to start our vcap system, and we should have four DEA nodes, and a dedicated MySQL node. As above, start our modified plan with::

    $ cloudinitd boot -v -v -v cloudfoundry-multi/main.conf -n cf-multi

Once it's completed, you'll have a system with a controller node, four DEAs, and a dedicated MySQL node.


.. _cloudinit.d documentation: http://www.nimbusproject.org/doc/cloudinitd/latest/
.. _Cloud Foundry README: https://github.com/cloudfoundry/vcap/blob/master/README.md
