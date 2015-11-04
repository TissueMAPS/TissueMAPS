
[![Build Status](http://jenkins.pelkmanslab.org/buildStatus/icon?job=tmlibrary_Master)](http://jenkins.pelkmanslab.org/job/tmlibrary_Master)

# Source code

**tmlib** is a Python package that serves as a library for image processing tasks within the [TissueMAPS](https://github.com/HackerMD/TissueMAPS) framework.


# Documentation

Documentation will ultimately be available on [readthedocs.org](https://readthedocs.org/).
For now, you'll have to build the documentation yourself:

and build the documentation website

    $ cd docs
    $ make clean
    $ make html

The generated HTML files are located at `./docs/_build/html`.

Note that if certain packages are only available within a virtual environment, the environment needs to be activated and sphinx needs to be installed in the environment such that the correct *SPHINXBUILD* is picked up. You can test this as follows:

    $ which sphinx-build

# Testing

Tests are run via [nosetests](https://nose.readthedocs.org/en/latest/) on [Jenkins](https://jenkins-ci.org/).
