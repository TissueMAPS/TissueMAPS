#!/bin/bash
#
# Create virtualenv for running tests and generating docs.
#
# The script expects to be run from the TOP-LEVEL folder of tmlibrary
#

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
if [[ ! -f requirements-Darwin-4.txt ]]; then
    echo "requirements-Darwin-3.txt is missing from the root directory of tmlibrary"
    exit 101
fi

VENV="${PWD}/venv_tmlibrary"

# Some packages require the latest pip version
if [[ ! $(pip -V) =~ "7.1.2" ]]; then
    echo "requires pip version 7.1.2"
    exit 101
fi

# Remove previous environment
if [ -d $VENV ]; then
  rm -r VENV
fi

# Create a fresh virtual environment
virtualenv -p /usr/bin/python2.7 $VENV

# Activate the virtual environment
source $VENV/bin/activate

# Install tmlib dependencies with `pip`
pip install -r requirements-1.txt
pip install -r requirements-2.txt
pip install -r requirements-3.txt
pip install -r requirements-git.txt

# NOTE: dependencies in requirements-Darwin-3.txt should be installed globally
# via apt-get
ln -s /usr/lib/python2.7/dist-packages/gi $VENV/lib/python2.7/site-packages/gi
ln -s /usr/lib/python2.7/dist-packages/cv2.so $VENV/lib/python2.7/site-packages/cv2.so
ln -s /usr/lib/python2.7/dist-packages/lxml $VENV/lib/python2.7/site-packages/lxml
ln -s /usr/lib/python2.7/dist-packages/rpy2 $VENV/lib/python2.7/site-packages/rpy2

# Install tmlib
pip install -e .
# pip install -e ./lib/pyfakefs

# Put command line scripts on the PATH
export PATH="./src/tmlib/bin:$PATH"

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

# Deactivate the virtual environment
deactivate
