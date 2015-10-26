**tmlib** is a Python package that serves as a library for image processing tasks within the `TissueMAPS <https://github.com/HackerMD/TissueMAPS>`_ framework.

Documentation will ultimately be available on `readthedocs.org <https://readthedocs.org/>`_.

For now, you'll have to build the documentation yourself:

Update the documentation upon changes in the source code

.. code:: bash

    $ sphinx-apidoc -o ./docs ./tmlib

and build the documentation website

.. code:: bash
    
    $ cd docs
    $ make html

The generated HTML files are located at `./docs/_build/html`.
