#!/bin/bash
#
# Runs tmlibrary test scripts in a controlled environment
#
# The script expects to be run from the TOP-LEVEL folder of tmlibrary
#

# exit at the first error
set -e

# Checks if we are in the top level folder
if [[ ! -d src ]] || [[ ! -d docs ]] || [[ ! -d scripts ]]; then
    echo "Please execute script from the top-level folder of tmlibrary"
    exit 100
fi

# Activate virtualenv
workon tmlibrary

#
# Actually run tests
#
nosetests -v ./src --all-modules --with-doctest \
    --with-xunit --xunit-file=global_nosetests.xml

# Deactivate virtualenv
deactivate
