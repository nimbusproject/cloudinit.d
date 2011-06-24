rpm -Uvh http://download.fedora.redhat.com/pub/epel/5/i386/epel-release-5-4.noarch.rpm
yum -y install python26-devel python26-distribute.noarch gcc
easy_install-2.6 cloudinitd
cloudinitd --help
