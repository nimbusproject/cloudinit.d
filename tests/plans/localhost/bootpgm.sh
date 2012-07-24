#!/bin/bash

if [ ! -e bootconf.json ]; then
    echo "The boot conf file does not exist!"
    pwd
    exit 1
fi
if [ ! -e bootenv.sh ]; then
    echo "The boot conf file does not exist!"
    pwd
    exit 1
fi

exit 0
