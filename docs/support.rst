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
    - metion other users via ``@<username>``
    - refer to other issues via ``#<issue_id>``


.. _troubleshooting:

Troubleshooting
===============

.. _troubleshooting-login:

Login
-----

Login via the browser is not possible.

Are servers (web, application and database server) running?

.. code-block::

    # NGINX
    sudo service nginx status

    # uWSGI
    sudo service uwsgi status

    # PostgreSQL (NOTE: The server may run on another machine!)
    sudo service postgresql status

What do log messages say?

.. code-block::

    # NGINX
    tail /var/log/nginx/tissuemaps-access.log
    tail /var/log/nginx/tissuemaps-error.log

    # uWSGI
    tail .tmaps/uwsgi.log

    # PostgreSQL (NOTE: The server may run on another machine!)
    tail /var/log/postgresql/postgresql-9.6-master.log

.. _debugging:

Debugging
=========

To debug `TissueMAPS` code outside of your production environment, you can either :doc:`install <installation>` it on your local machine or :doc:`setup <setup_and_deployment>` a `dev` instance in the cloud.

When you follow the installation or setup guide, `TissueMAPS` Python packages are installed in editable mode. Thereby, can simply set breakpoints (e.g. using `ipdb <https://pypi.python.org/pypi/ipdb>`_) or include ``print`` statements in the code.

.. tip:: You can find the files of installed packages locally with the following command (exemplified here for the `tmlib` package):

    .. code-block:: none

        python -c 'import tmlib; print tmlib.__file__'

.. _starting-dev-servers:

Starting the dev servers
------------------------

The `tmserver` package provides a development appliation server that can be started via the command line::

    tm_server

The `TmUI <https://github.com/TissueMAPS/TmUI/blob/master/src/gulpfile.js>`_ repository provides a development web server for the `tmaps` app. It can be started via the command line as follows (assuming that you cloned the repo into ``~/tmui`` and globally installed the required `npm` and `bower` packages)::

    cd ~/tmui/src
    gulp
