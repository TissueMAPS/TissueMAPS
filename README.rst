**********
TissueMAPS
**********

*TissueMAPS* is a software framework for distributed analysis and interactive visualization of large-scale, high-dimensional microscopy image datasets.

Online documentation is available at `docs.tissuemaps.org <http://docs.tissuemaps.org/>`_.


Quickstart
==========

*TissueMAPS* uses a distributed client-server model. The server exposes `RESTful web services <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ and clients interact with the server via the `REST API <http://www.restapitutorial.com/lessons/whatisrest.html>`_ using either the browser-based user interface or other client interfaces.

Server
------

To install the server components for development and testing, you can use the pre-build `Docker <https://www.docker.com/>`_ container images available on `Docker Hub <https://hub.docker.com/u/tissuemaps/dashboard/>`_::

    wget https://raw.githubusercontent.com/tissuemaps/tissuemaps/master/docker-compose.yml -q -P ~/tissuemaps
    cd ~/tissuemaps
    docker-compose up -d


For further details and alternative installation options, please refer to the `installation guide <http://tissuemaps.org/installation.html>`_ of the online documentation.


Client
------

Once you have access to a running server instance, you can interact with it via `HTTP <https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_ protocol.

Browser
^^^^^^^

The easiest way is to interact with the server is via the web-based user interface. To this end, point your web browser to ``http://localhost:8002``. This will redirect you to the login page. Once you have authenticated yourself using your credentials, you will see a list of your existing experiments.

cURL
^^^^

Alternatively, you could use `cURL <https://curl.haxx.se/>`_ to access resources via the command line:

Authenticate with your credentials:

.. code:: none

    curl --data '{"username": "devuser", "password": "123456"}' --header "Content-Type:application/json" http://localhost:8002/auth

List your existing experiments using the received `JSON web token <https://jwt.io/>`_ (replace ``XXX`` with the actual access token):

.. code:: none

    curl --header "Content-Type:application/json" --header "Authorization:JWT XXX" http://localhost:8002/api/experiments

TmClient
^^^^^^^^

*TissueMAPS* also provides a Python client that abstracts the *HTTP* interface and facilitas interaction with the server. You can install it via the `pip <https://pip.pypa.io/en/stable/>`_ Python package manager:

.. code:: none

    pip install tmclient

List your existing experiments using the ``tm_client`` command line tool:

.. code:: none

    tm_client -H localhost -P 8002 -u devuser -p 123456 experiment ls


Or using the ``tmclient`` Python package:

.. code:: python

    from tmclient import TmClient

    client = TmClient(host='localhost', port=8002, username='devuser', password='123456')
    experiments = client.get_experiments()
    print(experiments)


License
=======

Client code is licensed under `Apache 2.0 <https://www.apache.org/licenses/LICENSE-2.0.html>`_ and server code under `GNU Affero General Public License 3.0 <https://www.gnu.org/licenses/agpl-3.0.html>`_.

For more information please refer to the `license section <http://tissuemaps.org/license.html>`_ of the online documentation or the ``LICENSE.txt`` files in the individual Github repositories.
