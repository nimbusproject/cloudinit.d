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


What now?
---------

Now that you've seen that cloudinitd can start a single Cloud Foundry node, you
could try the cloudfoundry-multinode plan, and boot a multinode Cloudfoundry
installation. 

To do this, follow the same steps from the Boot Cloud Foundry section, but change
cloudfoundry to cloudfoundry-multi, like so::

    $ cloudinitd boot -v -v -v cloudfoundry-multi/main.conf -n cf-multi

.. _cloudinit.d documentation: http://www.nimbusproject.org/doc/cloudinitd/latest/
.. _Cloud Foundry README: https://github.com/cloudfoundry/vcap/blob/master/README.md
