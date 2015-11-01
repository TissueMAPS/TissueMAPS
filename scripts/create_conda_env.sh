#!/bin/bash
#
# Create tmlibrary virtualenv used to run tests and generate API docs.
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

# Makes sure requirements.txt is present
if [[ ! -f requirements-1.txt ]]; then
    echo "requirements-1.txt is missing from the root directory of tmlibrary"
    exit 101
fi
if [[ ! -f requirements-2.txt ]]; then
    echo "requirements-2.txt is missing from the root directory of tmlibrary"
    exit 101
fi
if [[ ! -f requirements-Darwin-3.txt ]]; then
    echo "requirements-Darwin-3.txt is missing from the root directory of tmlibrary"
    exit 101
fi

export PATH="/usr/bin:$PATH"
export PATH="/usr/local/lib:$PATH"

# Set path for virtual environment
export WORKON_HOME="$PWD/.virtualenvs"
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python
export VIRTUALENVWRAPPER_VIRTUALENV=/usr/local/bin/virtualenv

# Remove previous environment
if [ -d "$WORKON_HOME/tmlibrary" ]; then
  rmvirtualenv tmlibrary
fi

# Create and activates environment
mkvirtualenv tmlibrary

# Install tmlib dependencies with `pip`
pip install -r requirements-1.txt
pip install -r requirements-2.txt
pip install -r requirements-Darwin-3.txt

# Install tmlib
pip install -e .
pip install -e ./lib/pyfakefs
# It's a part of installation procedure that tmlib is installed
# into the homefolder.
export PYTHONPATH="$PWD/src:$PYTHONPATH"
export PYTHONPATH="$PWD/lib:$PYTHONPATH"

GC3PIE_DIR="$PWD/.gc3"
mkdir -p ${GC3PIE_DIR}
# create config file here in the Jenkins workspace (as opposed to the
# user's home directory)
export GC3PIE_CONF="${GC3PIE_DIR:-$PWD}/gc3pie.conf"
cat > "$GC3PIE_CONF" <<__EOF__
[resource/localhost]
enabled = yes
type = shellcmd
frontend = localhost
transport = local
max_cores_per_job = 1
max_memory_per_core = 1GiB
max_walltime = 8 hours
# this doubles as "maximum concurrent jobs"
max_cores = 4
architecture = x86_64
auth = none
override = no
__EOF__

# Deactivate virtual environment
deactivate
