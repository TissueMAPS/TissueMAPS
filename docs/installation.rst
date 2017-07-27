
************
Installation
************

*TissueMAPS* uses a distributed client-server model. As a consequence, client and server components typically need to be installed on different machines:

* **Client** code runs on the user's local machine and interacts with the server over `HTTP <https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_ protocol. No local installation is required for the web user interface, since the `Javascript` code is served via the web server and runs in the browser. Other client interfaces need to be installed locally, but they have very few dependencies and are easy to deploy on various platforms (Linux, MacOSX, Windows).

* **Server** code has many more dependencies and is designed for `UNIX <http://www.unix.org/what_is_unix.html>`_ platforms. The server may also run on the user's local machine during development and testing, but is typically deployed on a remote virutual machine (or multiple virtual machines) in the cloud.


If you don't use a dedicated machine, we recommend using a virtual environment for *TissueMAPS* related Python dependencies:

Install `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`_ and `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/>`_::

    pip install virtualenvwrapper

Add the following lines to your ``~/.bash_profile`` file:

.. code-block:: bash

    export WORKON_HOME=$HOME/.virtualenvs
    source /usr/local/bin/virtualenvwrapper.sh

Create a ``tissuemaps`` project::

    mkvirtualenv tissuemaps

You can deactivate the environment::

    deactivate

and later re-activate it when needed::

    workon tissuemaps

.. warning:: A coexisting `anaconda <http://docs.continuum.io/anaconda/pkg-docs>`_ installation doens't play nice with virtual environments and will create problems; see `potential solution <https://gist.github.com/mangecoeur/5161488>`_. Therefore, we prefer working with good old virtualenvs.


.. _clients-installation:

Clients
=======

Users can interact with the *TissueMAPS* server via a standard web browser (tested with `Chrome <https://www.google.com/chrome/>`_, `Firefox <https://www.mozilla.org/en-US/firefox/new/>`_ and `Safari <http://www.apple.com/safari/>`_) without the need to install any additional software locally.

Additional *HTTP* client implementations are available through the `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository.

.. _clients-installation-tmclient:

TmClient
--------

The :mod:`tmclient` Python package provides an active programming and command line interface.

Requirements
^^^^^^^^^^^^

* `Python <https://www.python.org/>`_: Many platforms are shipped with Python already pre-installed. If not, it can be downloaded from `python.org <https://www.python.org/downloads/>`_. Using version 2.7.9 or higher is recommended.
* `Pip <https://pip.pypa.io/en/stable/>`_: The Python package manager is automatically installed with Python distributions obtained from python.org. Otherwise, it can be installed with the `get-pip.py <https://bootstrap.pypa.io/get-pip.py>`_ script.
* `GCC <https://gcc.gnu.org/>`_ or similar compiler

Installation
^^^^^^^^^^^^

.. code-block:: none

    pip install tmclient


.. _server-installation:

Server
======

The server backend consists of the following core components:

* **Web server**: `NGINX <https://www.nginx.com/>`_
* **Dynamic web page**: `TmUI <https://github.com/TissueMAPS/TmUI>`_
* **Application server**: `uWSGI <https://uwsgi-docs.readthedocs.io/en/latest/>`_
* **Application**: `TmServer <https://github.com/TissueMAPS/TmServer>`_ and `TmLibrary <https://github.com/TissueMAPS/TmLibrary>`_
* **Database servers**: `PostgreSQL <http://postgresxl.org/>`_ with `Citus <https://www.citusdata.com/>`_ and `Postgis <http://postgis.net/>`_ extensions

and the following optional components, which are only required for a larger multi-machine cluster setup:

* **Compute servers**: `Slurm <http://slurm.schedmd.com/>`_ (job schedular and workload manager)
* **File system servers**: `GlusterFS <https://www.gluster.org/>`_ (scalable network file system)
* **Monitoring server**: `Ganglia <http://ganglia.info/>`_ (monitoring system)

All components are open-source and deployable on various public and private clouds.

.. _server-installation-cloud-images:

Public cloud images
-------------------

*TissueMAPS* provides publically accessible images on `Amazon Web Services (AWS) <https://aws.amazon.com/>`_ in form of shared `Amazon Machine Images (AMIs) <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/sharing-amis.html>`_.

Based on the images one can simply launch a virtual machine in the cloud via the `Elastic Compute Cloud (EC2) console <https://console.aws.amazon.com/ec2/>`_. To find the *TissueMAPS* images, filter public AMIs in the ``Frankfurt`` region for ``AMI Name: TissueMAPS server`` (see `AWS documentation <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/usingsharedamis-finding.html>`_).

.. _server-installation-docker:

Docker
------

*TissueMAPS* further provides pre-built container images, which are publicly available on `Docker hub <https://hub.docker.com/u/tissuemaps/dashboard/>`_. The easiest way to install the containerized application is via `Docker compose <https://docs.docker.com/compose/overview/>`_.

Requirements
^^^^^^^^^^^^

* `Docker CE <https://www.docker.com/community-edition>`_
* `Docker compose <https://docs.docker.com/compose/install/>`_

Installation
^^^^^^^^^^^^

Simply download the ``docker-compose.yml`` file and bring up the containers:

.. code-block:: none

    git clone https://github.com/tissuemaps/tissuemaps
    cd ~/tissuemaps
    docker-compose up -d

The first call will take a while because container images need to be downloaded. Subsequent calls will be highly responsive.


.. _server-installation-tmdeploy:

TmDeploy
--------

The :mod:`tmdeploy` Python package provides the ``tm_deploy`` program, which uses `Ansible <https://www.ansible.com/>`_ for

* provisioning and deployment of remote virtual machines (VMs) in the cloud
* building, running and shipping Linux containers

The program uses `Ansible playbooks <http://docs.ansible.com/ansible/playbooks.html>`_ and `Ansible container <https://docs.ansible.com/ansible-container>`_ to install and configure server components in virtual Linux environments (supported distributions: `Ubuntu 16.04 Xenial <http://releases.ubuntu.com/16.04/>`_ and `CentOS-7 <https://wiki.centos.org/Manuals/ReleaseNotes/CentOS7>`_). The same `Ansible roles <https://docs.ansible.com/ansible/playbooks_roles.html#roles>`_ are used for setting up cloud VMs and containers.

For more information on invididual roles, please refer to the `TmDeploy <https://github.com/TissueMAPS/TmDeploy/tree/master/tmdeploy/share/playbooks/roles>`_ repository.

Requirements
^^^^^^^^^^^^

* `Python <https://www.python.org/>`_: Many platforms are shipped with Python already pre-installed. If not, it can be downloaded from `python.org <https://www.python.org/downloads/>`_. Using version 2.7.9 or higher is recommended.
* `Pip <https://pip.pypa.io/en/stable/>`_: The Python package manager is automatically installed with Python distributions obtained from python.org. Otherwise, it can be installed with the `get-pip.py <https://bootstrap.pypa.io/get-pip.py>`_ script.
* `OpenSSH <https://www.openssh.com/>`_: Using version 7.2 or higher is recommended.
* `OpenSSL <https://www.openssl.org/>`_ (including the development libraries)
* `GCC <https://gcc.gnu.org/>`_ or similar compiler
* `Docker CE <https://www.docker.com/community-edition>`_ (optional, required for building containers): Download the community edition for your operating system from the `Docker Store <https://store.docker.com/search?type=edition&offering=community>`_. Also make sure that your operating system (OS) user has permissions to run the docker daemon. This can be achieved by adding the user to the *docker* group: ``sudo usermod -aG docker $(whoami)``.

Installation
^^^^^^^^^^^^

.. code-block:: none

    pip install tmdeploy

.. _server-installation-tmdeploy-container:

Build & Run Containers
^^^^^^^^^^^^^^^^^^^^^^

Containers are used for local development and testing. Setup is straight forward and doesn't require any additional configuration.

Usage
+++++

Build container images:

.. code-block:: none

    tm_deploy -vv container build

Create and run containers:

.. code-block:: none

    tm_deploy -vv container start

.. _server-installation-tmdeploy-vm:

Launch & Deploy VMs
^^^^^^^^^^^^^^^^^^^

Dedicated virtual machines are used for production deployment in the cloud. This requires a setup configuration file in `YAML <http://yaml.org/>`_ format (the default location of the file is ``~/.tmaps/setup/setup.yml``).

The setup configuration has two main sections:

- **cloud** (:class:`CloudSection <tmdeploy.config.CloudSection>`): Information about the cloud provider on which machines should be set up. Currently, three providers are supported:
    + ``os``: `OpenStack <http://www.openstack.org/>`_
    + ``ec2``: `Elastic Compute Cloud (Amazon Web Services) <https://aws.amazon.com/ec2/>`_
    + ``gce``: `Google Compute Engine <https://cloud.google.com/compute/>`_

- **architecture** (:class:`ArchitectureSection <tmdeploy.config.ArchitectureSection>`): Computational resources that should be set up and how they should be configured. The different server components (web server, application server, database servers, ...) may all be hosted on a single machine or get distributed across several machines. For consistency, **clusters** (:class:`ClusterSection <tmdeploy.config.ClusterSection>`) refers to sets of machines that get configured the same way - even if there is only a single machine. Each *cluster* is composed of one or more **node_types** (:class:`ClusterNodeTypeSection <tmdeploy.config.ClusterNodeTypeSection>`). *Nodes* belonging to a particular *node type* get assigned to one or more **groups** (:class:`AnsibleGroupSection <tmdeploy.config.AnsibleGroupSection>`), which determine how these *nodes* will be named and configured.

.. tip:: Copy one of the setup `templates <https://github.com/TissueMAPS/TmDeploy/tree/master/etc>`_ and modify it according to your needs.


Standalone (single-node) setup
++++++++++++++++++++++++++++++

The following `Ansible groups <http://docs.ansible.com/ansible/intro_inventory.html#hosts-and-groups>`_ are supported:

    * ``tisuemaps_server``
    * ``tissuemaps_db_master``
    * ``tissuemaps_db_worker``

.. TODO: variables

Example setup for the `Elastic Compute Cloud (EC2) <https://aws.amazon.com/ec2/>`_ provider based on a `CentOS 7 image <https://aws.amazon.com/marketplace/pp/B00O7WM7QW?qid=1499510484247&sr=0-1&ref_=srh_res_product_title>`_:

.. literalinclude:: ../src/tmdeploy/etc/singlenode_setup_ec2.yml
   :language: yaml
   :lines: 3-

This configuration will set up a single machine with 4 CPU cores and 3.75 GB of RAM per virtual CPU and create a seprate storage volume of 500GB size. Depending on your needs you may want to choose a different `machine type <https://cloud.google.com/compute/docs/machine-types>`_ and/or volume size. Note that when you omit the ``volume_size`` variable, no additional volume will be used and only the boot disk will be available.

.. note:: The resulting virtual machine instance will have the name ``tissuemaps-standalone-server-001``. This naming convention is a bit of an overkill for a single server. However, it becomes useful when building multiple clusters with different types of nodes. For consistency, we stick to this naming conventing also for simple standalone use case.


Cluster (multi-node) setup
++++++++++++++++++++++++++

Additional components can be configured using playbooks provided by `Elasticluster <http://gc3-uzh-ch.github.io/elasticluster/>`_. The following `Ansible groups <http://docs.ansible.com/ansible/intro_inventory.html#hosts-and-groups>`_ are supported:

    * ``tisuemaps_server``
    * ``tissuemaps_db_master``
    * ``tissuemaps_db_worker``
    * ``tisuemaps_compute``

    * ``glusterfs_server``
    * ``glusterfs_client``

    * ``slurm_master``
    * ``slurm_worker``

    * ``ganglia_master``
    * ``ganglia_monitor``

Example setup for the `Elastic Compute Cloud (EC2) <https://aws.amazon.com/ec2/>`_ provider based on a `CentOS 7 image <https://aws.amazon.com/marketplace/pp/B00O7WM7QW?qid=1499510484247&sr=0-1&ref_=srh_res_product_title>`_:

.. literalinclude:: ../src/tmdeploy/etc/cluster_setup_ec2.yml
   :language: yaml
   :lines: 4-

This configuration will set up one *TissueMAPS* server instance, one database coordinator server instance, two database worker server instances, two file system server instances, one monitoring server instance and eight compute instances. Depending on your needs, you may want to choose different number of nodes, machine types or volume sizes.

.. note:: *TissueMAPS* implements fair `scheduling <http://slurm.schedmd.com/sched_config.html>`_, based on `SLURM accounts <http://slurm.schedmd.com/accounting.html>`_. To enable this functionality, create *TissueMAPS* user accounts via the ``tm_add`` command line tool.

.. tip:: When deploying houndreds of compute nodes, it can be benefitial to use a pre-built image to speed up the cluster deployment process. To this end, configure a dedicated machine with only the ``tissuemaps_compute`` group and create a `snapshot <https://en.wikipedia.org/wiki/Snapshot_(computer_storage)>`_ of the configured instance. The thereby created image can then be reused to quickly boot additional machines for a large cluster setup.

Credentials
+++++++++++

To connect to the configured cloud, credentials are required, which must be provided via the following provider-specific environment variables:

* ``os`` provider:

  - ``OS_PROJECT_NAME``: name of the `project <http://docs.openstack.org/admin-guide/cli-manage-projects-users-and-roles.html>`_
  - ``OS_AUTH_URL``: URL of the identity endpoint
  - ``OS_USERNAME``: username
  - ``OS_PASSWORD``: password

* ``gce`` provider:

  - ``GCE_PROJECT``: name of the `project <https://cloud.google.com/compute/docs/projects>`_
  - ``GCE_EMAIL``: email associated with the *project*
  - ``GCE_CREDENTIALS_FILE_PATH``: path to JSON `credentials file <https://developers.google.com/identity/protocols/application-default-credentials>`_

* ``ec2`` provider:

  - ``AWS_ACCESS_KEY_ID``: `access key <http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSGettingStartedGuide/AWSCredentials.html>`_
  - ``AWS_SECRET_ACCESS_KEY``: corresponding secret access key

.. tip:: It can be convenient to place these variables into a ``~/.credentials.sh`` file:

    .. code-block:: bash

        export AWS_ACCESS_KEY_ID=XXX
        export AWS_SECRET_ACCESS_KEY=XXX

    and source the file prior to running ``tm_deploy``::

        source ~/.credentials.sh

Usage
+++++

Launch virtual machine instances in the cloud:

.. code-block:: none

    tm_deploy -vv vm launch

The ``launch`` command calls the `instance.yml <https://github.com/TissueMAPS/TmDeploy/blob/master/tmdeploy/share/playbooks/instance.yml>`_ playbook.

.. note:: The ``tm_deploy`` program will by default look for a setup file at the following location: ``~/.tmaps/setup/setup.yml``. Alternatively, the path to the file can be specified via the ``--setup-file`` or ``-s`` flag.

.. note:: An *SSH* key pair will be automatically created on the local machine and uploaded to the cloud. The generated key files will be placed into ``~/.ssh``. The name of the key pair is determined by :attr:`key_name <tmdeploy.config.CloudSection.key_name>`.

.. note:: A private :attr:`network <tmdeploy.config.CloudSection.network>` and :attr:`subnetwork <tmdeploy.config.CloudSection.subnetwork>` will get automatically created. In addition, each node gets assigned to one or more security groups (firewall) rules based on the configured :attr:`tags <tmdeploy.config.AnsibleHostVariableSection.tags>`. Only machines tagged with ``web`` will get a public IP and can be directly accessed via *SSH*, ``HTTP`` and ``HTTPS`` on ports 22, 80 and 443, respectively. The other machines are only accessible from within the private network. ``tm_deploy`` uses an *SSH* ``ProxyCommand`` to connect to machines within the private network using a ``web`` tagged machine as a *bastion host*.


Deploy *TissueMAPS* on virtual machine instances:

.. code-block:: none

    tm_deploy -vv vm deploy

The ``deploy`` command runs the following playbooks:

    - `site.yml <https://github.com/TissueMAPS/TmDeploy/blob/master/tmdeploy/share/playbooks/elasticluster/site.yml>`_ for roles provided via the `elasticluster <https://elasticluster.readthedocs.io/en/latest/>`_ package in case additional, non-core groups are specified in the setup configuration
    - `site.yml <https://github.com/TissueMAPS/TmDeploy/blob/master/tmdeploy/share/playbooks/tissuemaps/site.yml>`_ of the :mod:`tmdeploy` package


Terminate virtual machine instances:

.. code-block:: none

    tm_deploy -vv vm terminate

.. note:: The ``terminate`` command will remove virtual machine instances and storage volumes, but networks and security groups won't get deleted.

