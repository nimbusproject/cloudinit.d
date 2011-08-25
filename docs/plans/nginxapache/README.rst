Load balanced web server
========================

Introduction
------------

This example plan will setup several apache servers fronted by an nginx 
load balancer.


Prerequisites
-------------

Ensure that you have cloudinit.d installed. See the [cloudinit.d documentation]
for instructions.

Ensure that you have your IaaS credentials exported into your environment::

    $ export CLOUDINITD_IAAS_ACCESS_KEY=<EC2 access key>
    $ export CLOUDINITD_IAAS_SECRET_KEY=<EC2 secret key>
    $ export CLOUDINITD_IAAS_SSHKEY=<EC2 ssh key name>
    $ export CLOUDINITD_IAAS_SSHKEYNAME=<path to the matching ssh key>

Boot The Launch Plan
--------------------

Once you have your credentials set up, you need to build a tarball for both the
Chef cookbooks used to build your webserver installation.  This processes is
scripted, so change to your plans directory and run the following::

    $ cd plans
    $ ./common/prepare-tarball.sh
    Created cookbooks.tar.gz
    $ ./cloudfoundry/01/prepare-tarball.sh 
    Created readytests.tar.gz

If you later modify the cookbooks, or the readytests, you will
need to re-run these scripts before you re-deploy the launch plan.

Now run cloudinit.d to boot a single node installation::

    $ cloudinitd boot -v -v -v nginxapache/main.conf webfarm
    Starting up run webfarm
        Started IaaS work for apache2
    Starting the launch plan.
    Begin boot level 1...
        Started apache2


Testing Installation
--------------------

To test your installation, simply point a web browser at the ip addresses
printed out for the ngix service.  You should get a basic web page telling
you what backend host you were redirected to.  This should change with
ever load of the page.

Teardown
--------

It is important to cleanup all the allocated resources.  To do this, run the
following::

    $ cloudinitd terminate webfarm
    Terminating webfarm
    SUCCESS level 2
    SUCCESS level 1

