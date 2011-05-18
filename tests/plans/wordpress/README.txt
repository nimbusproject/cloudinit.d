cloudinit.d wordpress example
=============================

Prerequisites
------------

For this example to work you need your default security group to have 
port 22, 80 and 3306 open.

boot
----

This example launch plan will launch 2 standard ubuntu 10.10 images provided
by the EC2 AMI ami-ccf405a5.  The first instance will be setup to run mysql.
How it is setup is described in the python program mysql_boot.py.  The
second instance will be setup to run a wordpress service which uses
the previous instance's mysql service.  The details of its setup are 
described in wordpress_boot.py

Once the plan is successfully launched the webpage:

http://<wordpress service hostname>/wordpress/wp-admin/install.php

will be ready for the user to setup their wordpress service.

The value for <wordpress service hostname> can be found by looking in 
the log files under ~/.cloudinitd/ or via the console output when 
-v -v is used.

Example session:
----------------

First we boot that launch plan:

    $ cloudinitd -v -v -v -v boot top.conf 
    Starting up run a5dcab27
        Have instance id i-4acf6625 for mysql
        Started IaaS work for mysql
        Have instance id i-40cf662f for wordpress
        Started IaaS work for wordpress
    Starting the launch plan.
    Begin boot level 1...
        Started mysql
        Have hostname ec2-67-202-37-183.compute-1.amazonaws.com
        retrying the command
        retrying the command

        SUCCESS service mysql boot
            hostname: ec2-67-202-37-183.compute-1.amazonaws.com
            instance: i-4acf6625
    SUCCESS level 1
    Begin boot level 2...
    Begin boot level 2...
        Started wordpress
        Have hostname ec2-184-72-89-233.compute-1.amazonaws.com

        SUCCESS service wordpress boot
            hostname: ec2-184-72-89-233.compute-1.amazonaws.com
            instance: i-40cf662f
    SUCCESS level 2

Now we can use a web browser to navigate to:
     http://ec2-184-72-89-233.compute-1.amazonaws.com/wordpress/wp-admin/install.php

Now we clean up the service to avoid further EC2 charges:

    Terminating a5dcab27
    Begin terminate level 2...
        Started wordpress
        SUCCESS service wordpress terminate
            hostname: None
            instance: None
    SUCCESS level 2
    Begin terminate level 1...
    Begin terminate level 1...
        Started mysql
        SUCCESS service mysql terminate
            hostname: None
            instance: None
    SUCCESS level 1



