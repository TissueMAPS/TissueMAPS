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

export PATH="/usr/bin:$PATH"
export PATH="/usr/local/lib:$PATH"

# Set path for virtual environment
export WORKON_HOME="$PWD/.virtualenvs"
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python
export VIRTUALENVWRAPPER_VIRTUALENV=/usr/local/bin/virtualenv
source /usr/local/bin/virtualenvwrapper.sh

# Create a link for vips
cd $VIRTUALENVWRAPPER_HOOK_DIR/tmlibrary/lib/python2.7/site-packages/gi
ln -s /usr/local/lib/python2.7/site-packages/gi gi

# Activate virtualenv
workon tmlibrary

#
# Actually run tests
#
nosetests -v ./src --all-modules --with-doctest \
    --with-xunit --xunit-file=global_nosetests.xml

# Deactivate virtualenv
deactivate
