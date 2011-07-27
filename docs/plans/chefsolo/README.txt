chef-solo
=========

This example shows how to launch a single VM with cloudinit.d.  This is a 
simple example designed to provide a quick introduction to cloudinit.d used
with chef-solo for configuration.

In it we will create the configuration files needed to contact EC2 and launch
a known AMI, configure it via chef recipes, and see the result.


Prerequisites
-------------

Before you begin you will need 4 standard pieces of information from your
EC2 account.  See the "helloec2" plan for more information (it will behoove
you to actually read that README as well if you have not).


Examine the cookbooks
---------------------

TODO: talk about how basenode.json lists the recipes to run (ordered list)
TODO: talk about common/cookbooks directory


Run the sample
--------------

$ ../common/prepare-tarball.sh
$ cloudinitd boot main.conf -v -v -v -l debug 

TODO: talk about this error:
Exception: File does not exist: 'common/cookbooks.tar.gz'

