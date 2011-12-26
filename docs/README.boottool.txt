cloudinit.d
===========

cloudinit.d is a tool for launching and configuring a set of 
interdependent VMs in a cloud (or set of clouds).

The most primitive feature of cloudinit.d is the ability to launch and 
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

To launch this application with cloudinit.d the NFS VM and the Postgres 
VM would be put into boot level 1, and the 3 Apache VMs would be put 
into boot-level 2.

Not only do the web server VMs need the NFS and Postgres to exist, but 
they also need to know various bit of information about there specific 
instances (like the IP address).  cloudinit.d provides a mechanism to 
query lower boot level VMs from information.  Thus it is a complete tool 
for launching many interdependent virtual machines.

Booting and configuring a single instance
-----------------------------------------

Before diving into the details of boot level creation we must first 
explain how to launch and configure a single VM with cloudinit.d.  As 
input cloudinit.d takes a set of configuration files (these will be 
discussed in detail later).  Here we will just introduce the 'service' 
section of the configuration file.  This is the part of the 
configuration that describes a single VM instance and how it should be 
launched, configured, and tested.  Below is a sample service section:


    [svc-webserver]
    image: ami-blahblah
    iaas: us-east-1
    ssh_username: ubuntu
    allocation: m1.small
    sshkeyname: ooi
    localsshkeypath: ~/.ssh/ooi.pem
    readypgm: /opt/sample/sample-test.sh
    bootpgm: setuphost.sh
    bootconf: sample.json
    deps1: sample-deps.conf
    deps2: <other dep files>


Here cloudinit.d is instructed to launch the image 'ami-blahblah' in the 
cloud 'us-east-1'.  The sshkeyname is the security handle known by the 
cloud and localsshkeypath is the path a key on the local file system.  
Allocation is the type (or size) of the instance required.  All of those 
values are the information needed just to launch an image in the cloud 
and the security handles to access it.

The last four values are used to setup the VM once it is launched.  
Often times it is of value to launch a standard VM and customize it 
(install needed software, setup user accounts, etc) after it has begun.  
The bootpgm key points to a file that is uploaded to the VM and run as 
root via sudo (this implies that the ssh_username account must be able 
to run sudo without a password).  The intention of the bootpgm is to set 
up the VM.  The user can run any command it likes at their own risk.  
The remaining keys allow the user to pass variable information from on 
VM to another and are described in the next section.

The next parameter 'readypgm' is a path to a localfile that tests to see 
if the VM is ready for use.  Once the VM is launched and configured this 
file is transferred to it and run.  The program should check to see that
all services needed by this host are running properly and thus the 
machine is ready to be used.  The program should block until either it 
determines that machine and all of its services have booted and are 
ready to go, or it determines that the boot definitively failed.  The 
read_timeout parameter describes in seconds how long to wait for the VM 
to be ready before timing out and thus considering the boot a failure.

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
    database_ip: ${database.ipaddress}


This tells cloudinit.d to look at all the previous boot levels and search 
for a service named [svc-database].  Once found it is told to ask that 
service the value of its variable 'ipaddress'.  This information can 
then be used by the bootpgm to properly launch the [svc-webserver].

Boot-level Files
---------------

Now that we can describe a single VM and a way to get dynamic variables 
from 1 VM to another, we can talk about how to arrange them into 
boot-levels.

Each boot-level is a single configuration file that consists of [svc-*] 
sections as described above. (Details on the svc-* sections can be found 
in sample-level.conf).  Every service in this section is started, 
configured and tested at the same time.  They have no dependencies
between each other.  The boot level is not considered complete until
every single service has started and its ready program has completed
successfully.  If any svc fails, the entire boot level fails.

Once we have boot levels described we simply need to describe their 
order. This is done in a top-level configuration file.  (see 
sample-top.conf for details).  Here is an example:

    [runlevels]
    level1: sample-level1.conf
    level2: level2.conf
    level3: level3.conf
    level4: level4.conf

This is a very basic configuration file that lists the run levels in 
order by pointing at the configuration file for each level.

bootpgm and readypgm
--------------------

There are no restrictions imposed upon these programs.  The 
responsibility of creating safe programs that do the intended function 
is entirely upon the user.  The programs are uploaded to the VMs /tmp 
directory and run as root. cloudinit.d expects that bootpgm will 
contextualize the system (anyway it wants) and it expects the readypgm 
to return a 0 or a 1 stating if the system is ready or not.

The value for each program can be a single executable file, or it can be 
tarball.  If the filename ends in 'tar.gz' cloudinit.d will upload it, 
then run tar -zxf on it.  It expects the tarball to contain a single 
root with the same name as itself, without the tar.gz extension.  It 
further expects all of the files to be under that directory including an 
executable named 'run.sh'.  As soon as the expansion of the tarball is 
complete 'run.sh' is executed.

The bootpgm program can take advantage of the bootconf json file.  This 
file can be full of variables from values determined by the given 
services dependencies.  The user creates the template for this file and 
uses the plan configuration value 'bootconf' to tell cloudinit.d where the 
template is.  cloudinit.d then uses all the values it has from the 
services 'deps' file to fill in the template. This file is always 
uploaded to: /tmp/nimbusconf/bootconf.json.  The users bootconf program 
can read it in to determine the needed values.
