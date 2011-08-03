#!/bin/bash
set -e

cd ~/cloudfoundry/vcap/cloud_controller

rake spec
cd ../dea
rake spec
cd ../router
rake spec
cd ../health_manager
rake spec

