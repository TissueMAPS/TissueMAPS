***************************
Support and troubleshooting
***************************

.. _issue-tracker:

Issue tracker
=============

If you have a question or feature request or you want to report a bug, please use the `Github issue tracker <https://github.com/TissueMAPS/TissueMAPS/issues>`_.

.. _creating-an-issue:

Creating an issue
-----------------

`Here <https://help.github.com/articles/creating-an-issue/>`_ you find help on how to create an issue on Github.

Before creating an issue, check whether there is already an existing issue describing your problem.

When creating an issue

    - create a separate issue report for orthogonal topics
    - use `Markdown <https://help.github.com/articles/about-writing-and-formatting-on-github/>`_ syntax
    - provide an error traceback from a log message whenever possible
    - embed screenshots for UI related topics (you can simply drag and drop the image into the text input field)
    - provide tags of git commits or Docker container images
    - metion other users via ``@<user>``
    - refer to other issues via ``#<issue-number>``
    - refer to commits via ``<user>/<repository>@<commit-tag>``


.. _debugging:

Debugging
=========

*TissueMAPS* Python packages are installed in editable mode. Therefore, you can simply set breakpoints (e.g. using `ipdb <https://pypi.python.org/pypi/ipdb>`_) or include ``print`` statements in the code.


.. _using-dev-servers:

Using dev servers
-----------------

The development servers are convenient for debugging because they provide live-reload functionality, i.e. they automatically reload when *TissueMAPS* code get's changed.

The `tmserver` package provides a development appliation server that can be started via the command line::

    tm_server

The `TmUI <https://github.com/TissueMAPS/TmUI/blob/master/src/gulpfile.js>`_ repository provides a development web server for the `tmaps` app. It can be started via the command line as follows (assuming that you cloned the repo into ``~/tmui`` and globally installed the required `npm` and `bower` packages)::

    cd ~/tmui/src
    gulp

The web server will listen to port 8002: ``http://localhost:8002``


If you use the Docker containers, you can use the ``docker-compose.dev_override.yml`` configuration to start containers with development servers:

.. code-block:: none

    wget https://raw.githubusercontent.com/tissuemaps/tissuemaps/master/docker-compose.yml -q -P ~/tissuemaps
    wget https://raw.githubusercontent.com/tissuemaps/tissuemaps/master/docker-compose.dev_override.yml -q -P ~/tissuemaps
    cd ~/tissuemaps
    docker-compose -f docker-compose.yml -f docker-compose.dev_override.yml up
