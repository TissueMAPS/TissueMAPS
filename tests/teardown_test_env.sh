#!/bin/bash

echo "Stop Docker containers"
tm_deploy container stop

echo "Deactivate Python virutual environment"
deactivate

exit 0
