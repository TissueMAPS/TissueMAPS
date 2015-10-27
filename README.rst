**tmlib** is a Python package that serves as a library for image processing tasks within the `TissueMAPS <https://github.com/HackerMD/TissueMAPS>`_ framework.

Documentation will ultimately be available on `readthedocs.org <https://readthedocs.org/>`_.

For now, you'll have to build the documentation yourself:

Update the documentation upon changes in the source code

.. code::

    $ sphinx-apidoc -o ./docs ./tmlib

and build the documentation website

.. code::
    
    $ cd docs
    $ make clean
    $ make html

The generated HTML files are located at `docs/_build/html <./docs/_build/html>`_.

Note that if certain packages are only available within a virtual environment, the environment needs to be activated and sphinx needs to be installed in the environment such that the correct *SPHINXBUILD* is picked up. You can test this as follows:

.. code::
    
    $ which sphinx-build
