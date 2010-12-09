cloud-boot
==========

cloud-boot is a tool for launching and configuring a set of 
interdependent VMs in a cloud (or set of clouds).

The most primitive feature of cloud-boot is the ability to launch and 
configure Virtual Machines.  That building block is used to arrange 
'boot levels'.  Any one boot-level is a collection of VMs that can be 
launched at the same time and have no dependencies on each other. 
However, Any VM that is running in boot-level N can depend on values and 
attributes from any VM run in boot-level N - 1.

Boot Level Example
------------------

To further explain boot level we lay out an example.  Let say we want to 
run a database driven web application.  This application requires 3 
instances of the apache web server (for load balancing), all of which 
source the same static content from a shared file system and interact 
with the same postgres database.  This application needs the following 
Virtual Machines:

- an NFS server
- a postgres database
- 3 apache web servers

The web server VMs mount the NFS file system and connect to the postgres 
database, thus they cannot be started until the NFS VM and the postgres 
VM are started.

To launch this application with cloud-boot the NFS VM and the Postgres 
VM would be put into boot level 1, and the 3 Apache VMs would be put 
into boot-level 2.

Not only do the web server VMs need the NFS and Postgres to exist, but 
they also need to know various bit of information about there specific 
instances (like the IP address).  Cloud-boot provides a mechanism to 
query lower boot level VMs from information.  Thus it is a complete tool 
for launching many interdependent virtual machines.

Booting and configuring a single instance
-----------------------------------------

Before diving into the details of boot level creation we must first 
explain how to launch and configure a single VM with cloud-boot.  As 
input cloud-boot takes a set of configuration files (these will be 
discussed in detail later).  Here we will just introduce the 'service' 
section of the configuration file.  This is the part of the 
configuration that describes a single VM instance and how it should be 
launched, configured, and tested.  Below is a sample service section:


    [svc-webserver]
    image: ami-blahblah
    iaas: ec2-east
    allocation: m1.small
    sshkeyname: ooi
    localsshkeypath: ~/.ssh/ooi.pem
    bootconf: sample.json
    ready: /opt/sample/sample-test.sh
    ready_timeout: 0
    deps: sample-deps.conf


Here cloud-boot it instructed to launch the image 'ami-blahblah' in the 
cloud 'ec2-east'.  The sshkeyname is the security handle known by the 
cloud and localsshkeypath is the path a key on the local file system.  
Allocation is the type (or size) of the instance required.  All of those 
values are the information needed just to launch an image in the cloud 
and the security handles to access it.

XXXX still being worked out XXXX 
The last four values are cloud-boot specific.  bootconf is a path to a 
file that is used as input to chef solo.  Chef solo is responsible for 
configuring the system env.  This combined with the image ID creates a 
fully configured virtual machine.

The next parameter 'ready' is a path to a localfile that tests to see if 
the VM is ready for use.  Once the VM is launched and configured with 
chef, this file is transfered to it and run.  The program should check 
to see that all services needed by this host are running properly and 
thus the machine is ready to be used.  The program should block until 
either it determines that machine and all of its services have booted 
and are ready to go, or it determines that the boot definitively failed.  
The read_timeout parameter describes in seconds how long to wait for the 
VM to be ready before timing out and thus considering the boot a 
failure.

The final value, deps is a list of key value pairs both needed by this 
VM and provided by this VM to other VMs.  This parameter will be 
discussed in the next section.

Service Deps
------------

We see above how to create a single stands- alone VM.  Now we will 
discuss how to create a VM that depends on other VMs, and more 
specifically, how to to get needed variables from those dependencies.

In the above example we have a web server that depended on a database. 
The database VM is launched in level 1 and the web server is launched in 
level 2.  In order for the web server to connect to the database it 
needs that VM's IP address.  However, this is unknown until the database 
VM is launched and running.  It is not information that can be 
prearranged in the boot-script, instead it must be dynamically 
determined at runtime.

The 'deps' file provides a way to describe the values the associated VM 
needs from those run in a previous boot level.  In our example where the 
[svc-webserver] VM needs the IP of a [svc-database] the deps file for 
the svc-webserver would have the following:


    [deps]
    database_ip: ${database}.ipaddress


This tells cloud-boot to look at all the previous boot levels and search 
for a service named [svc-database].  Once found it is told to ask that 
service the value of its variable 'ipaddress'.  This information is then 
used with chef solo and the bootconf file to properly launch the 
[svc-webserver]. * exactly how this information is passed around will be 
discussed later

Boot-level Files
---------------

Now that we can describe a single VM and a way to get dynamic variables 
from 1 VM to another, we can talk about how to arrange them into 
boot-levels.

Each boot-level is a single configuration file that consists of [svc-*] 
sections as described above. (Details on the svc-* sections can be found 
in sample-level.conf).  Every service in this section is started, 
configured and tested at the same time.  The have no dependencies on 
each.  The boot level is not considered complete until every single 
service has started and its ready program has completed successfully.  
If any svc fails, the entire boot level fails.

Once we have boot levels described we simply need to describe their 
order. This is done in a top-level configuration file.  (see 
sample-top.conf for details).  here is an example:

    [runlevels]
    level1: sample-level1.conf
    level2: level2.conf
    level3: level3.conf
    level4: level4.conf

This is a very basic configuration file that lists the run levels in 
order by pointing at the configuration file for each level.




