#!/bin/bash
#
# Create iBRAIN conda env used to run tests and generate API docs.
#
# The script expects to be run from the TOP-LEVEL folder of iBRAIN_UZH
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

conda install conda-env --yes -q

# Removes previous environment
conda-env remove -n tmlibrary --yes -q

# Creates and activates environment
conda create -n tmlibrary python --yes -q
source activate tmlibrary

# Use `pip install` from activated conda PATH
export PATH="$HOME/.local/bin:$PATH"

# Install GC3Pie and configure it to run tasks on local host only
#
# Note: we cannot use GC3Pie's `install.sh` script as that only
# works with Python "virtualenv"s, whereas we are using Anaconda's
# environment feature, which is a different beast.
#
: ${required_gc3pie_version:='2.4.0'}
case "$required_gc3pie_version" in
    *dev*)
        # install development version from SVN
        gc3pie_dir="$PWD/gc3pie"
        if [ -d "$gc3pie_dir" ]; then
            # assume source is already checked out here, update
            (cd "$gc3pie_dir" && svn update)
        else
            # perform SVN checkout
            svn checkout --quiet http://gc3pie.googlecode.com/svn/trunk/gc3pie "$gc3pie_dir"
        fi
        # install GC3Pie package
        (cd "$gc3pie_dir" && pip install -e .)
        ;;
    *)
        # install released version from PyPI
        pip install "gc3pie==${required_gc3pie_version}"
        ;;
esac
# create config file here in the Jenkins workspace (as opposed to the
# user's home directory)
export GC3PIE_CONF="${gc3pie_dir:-$PWD}/config.ini"
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


# Install brainy and its dependencies with `pip` as not all of them
# are available as Conda packages, and furthermore `conda develop`
# does not install/create the executables
# XXX: an alternative way to run `brainy` tests is `python setup.py test`
pip install -r requirements-1.txt
pip install -r requirements-2.txt

# Install tmlib
pip install -e .
# It's a part of installation procedure that tmlib is installed
# into the homefolder.
export PYTHONPATH="$PWD/src:$PYTHONPATH"

# Deactivates Anaconda
source deactivate
