#!/bin/bash
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

# Activate environment created by test_all_packages script.
workon tmlibrary

# Generates docs.
sphinx-apidoc -o docs src/tmlib
make -C docs html

# Deactivate virtual environment
deactivate tmlibrary
