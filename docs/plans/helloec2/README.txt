Hello EC2
=========

This example shows how to launch a single VM with cloudinit.d.  This is a 
very rudimentary example designed to provide a quick introduction to 
cloudinit.d.  In it we will create the configuration files needed to 
contact EC2 and launch a known AMI and to test that VM to determine when
it is ready.

Prerequisites
------------

Before you begin you will need 4 standard pieces of information from your
EC2 account.

    - access key (this is akin to your EC2 login ID)
    - access secret (this is akin to your EC2 password)
    - ec2 key name
    - path to the matching local ssh key

If you have ever launched a VM on EC2 you have all of this information.  If
not you will need to sign up for an EC2 account to get it.

Further, in order to make this work your default security group on EC2 
must have port 22 open.

Try it out
----------

Before we dive into the details of the example lets try it out  First, boot
the plan (note: running this command successfully is subject to amazon
web services pricing, currently $0.025 per hour).

    $ cloudinitd -v -v -v boot helloec2.conf 
    Starting up run 8d5e0753
        Started IaaS work for sampleservice
    Starting the launch plan.
    Begin boot level 1...
        Started sampleservice
        SUCCESS service sampleservice boot
            hostname: ec2-50-17-8-151.compute-1.amazonaws.com
            instance: i-1255f67d
    SUCCESS level 1

Here we see that we booted the plan.  The option -v simply increases the 
amount of output that we will see.  The messages printed to the console
tell us the run name and that the plan was successfully launched.

Let us say that a few hours have past and we want to check on the status of
our ec2 cloud application.  To do so we need to remember the run name 
which was printed out above and then run:

    Checking status on 8d5e0753
    Begin status level 1...
        Started sampleservice
        SUCCESS service sampleservice status
            hostname: ec2-50-17-8-151.compute-1.amazonaws.com
            instance: i-1255f67d
    SUCCESS level 1

The output here shows that everything is still successfully running.

Now we shall terminate the cloud application with the following command:

    $ cloudinitd -v -v -v terminate 8d5e0753
    Terminating 8d5e0753
    Begin terminate level 1...
        Started sampleservice
        SUCCESS service sampleservice terminate
            hostname: None
            instance: None
    SUCCESS level 1
    deleting the db file /home/bresnaha/.cloudinitd/cloudinitd-8d5e0753.db

Configuration Plan
------------------

To find out what happened we must explore the configuration files.  There 
are two files, the top level configuration file helloec2.conf and the 
level configuration file, helloec2_level1.conf.

We start by looking at the very simple helloec2.conf which contains the 
following:

    [runlevels]
    level1: helloec2_level1.conf

all this does is tell cloudinit.d that there is 1 level and it is described
in the file helloec2_level1.conf.  A more complicated application would 
have more levels.

Now we look at the file helloec2_level1.conf:

    [svc-sampleservice]

    iaas_key: env.CLOUDBOOT_IAAS_ACCESS_KEY
    iaas_secret: env.CLOUDBOOT_IAAS_SECRET_KEY
    localsshkeypath: env.CLOUDBOOT_IAAS_SSHKEY
    keyname: env.CLOUDBOOT_IAAS_SSHKEYNAME

    ssh_username: ubuntu
    image: ami-30f70059
    allocation: t1.micro

    bootpgm: bootpgm.py

in it we see that a single service call 'sampleservice' is described.  The
first four lines tell cloudinit.d where the needed information described 
above can be found.  The prefix 'env.' is a directive to check the 
environment variable of the following name for the value in question.

The next three lines describe the image to be launch.  Here we will launch
the ubuntu10.10 AMI already stored in EC2.  The allocation field allows 
us to decide how much hardware we need.  For the sake of of saving money
we have chosen the micro instance.  The ssh_username field is the user name 
that the VM image has configured to allow access via your local ssh key.
In the case of the ubuntu image this value is 'ubuntu'.

The final value is the bootpgm.  This value is a script that will be uploaded
and run on the VM.  This is your opportunity to contextualize your VM instance
with needed values.  In our case we simply create a basic web page:

    #!/usr/bin/env python

    import sys
    import os

    f = open("hello.html", "w")
    f.write("<html><body>Hello cloudinit.d!</body></html>")
    f.close()

    cmd = "sudo cp hello.html /var/www/"
    os.system(cmd)

    sys.exit(0)

This simple python script opens a file and writes an html message.  It then
uses the pre-configured sudo access (common on ubuntu images) to copy the
web page to location that the apache2 web server will display.

Once you boot this plan goto: http://<ec2 hostname>/hello.html and you will
see the message created in the bootpgm.py script.


