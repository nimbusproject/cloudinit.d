#!/bin/bash

source bootenv.sh

if [ -z "$vcap_domain" ] ; then
    vcap_domain="vcap.me"
fi

if [ -z "$api_host" ] ; then
    api_host="api.$vcap_domain"
fi

cd $1 
vmc target $api_host
vmc register --email foo@bar.com --passwd password
vmc login --email foo@bar.com --passwd password
vmc delete env # Delete just in case left from a failed run

# the above may already be there and i cannot seem to clean them up
set -e
vmc push env --instances 4 --mem 64M --url env.$vcap_domain -n

curl  http://env.$vcap_domain | grep "Hello from the Cloud"
vmc apps | grep "env.$vcap_domain"

vmc delete env
