#!/bin/bash
#
# Runs tmlibrary test scripts in a controlled environment
#
# The script expects to be run from the TOP-LEVEL folder of tmlibrary
#

# Checks if we are in the top level folder
if [[ ! -d src ]] || [[ ! -d docs ]] || [[ ! -d scripts ]]; then
    echo "Please execute script from the top-level folder of tmlibrary"
    exit 100
fi

VENV="${PWD}/venv_tmlibrary"

export PYTHONPATH="/usr/lib/python2.7/dist-packages:/usr/local/bin/python2.7/site-packages:$PYTHONPATH"

# Set paths for Vips
export VIPSHOME=/usr/local
export GI_TYPELIB_PATH=$VIPSHOME/lib/girepository-1.0
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$VIPSHOME/lib

# Activate the virtual environment
source $VENV/bin/activate

#
# Actually run tests
#
nosetests -v ./src --all-modules --with-doctest \
    --with-xunit --xunit-file=global_nosetests.xml

# Deactivate virtualenv
deactivate
