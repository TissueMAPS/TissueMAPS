.. _cloud-setup-and-deployment:

**************************
Cloud setup and deployment
**************************

Manual installation and configuration, as described in the :doc:`installation <installation>` section, is feasible for a single machine. However, to run `TissueMAPS` in a distributed cluster environment in the cloud, manual setup becomes labor intensive and error-prone.

`TissueMAPS` uses `Ansible <https://www.ansible.com/>`_ for automation of application deployment.
The `TmSetup <https://github.com/TissueMAPS/TmSetup>`_ repository provides tools for automated setup and deployment on `Ubuntu 14.04 <http://releases.ubuntu.com/14.04/>`_.

In the following section, we will go through the steps required to setup and deploy `TissueMAPS` in the cloud a fully automated manner.

.. _requirements:

Requirements
============

.. _requirements-hardware:

Hardware
--------

In principle, deployment could be performed from any machine. We have only used Linux machines for deployment so far, however.

.. _requirements-connection:

Connection
----------

.. _requirements-connection-ssh-key:

SSH keys
^^^^^^^^

Connections to remote machines in the cloud are established via the `Secure Shell (SSH) <https://en.wikipedia.org/wiki/Secure_Shell>`_ protocol with key-based authentication.

On the deploying machine, create a `SSH` key-pair (here called ``tmaps``) and place it into ``~/.ssh``::

    ssh-keygen -f ~/.ssh/tmaps

Ensure that the key file has the correct permission::

    chmod 400 ~/.ssh/tmaps

and disable host key checking in the `SSH` configuration file ``~/.ssh/config``::

    Host *
        StrictHostKeyChecking no

.. note:: Amazon Web Serices requires the public key in a ``.pem`` file. You can create this key file using the following command: ``ssh-keygen -f ~/.ssh/tmaps -e -m pem > ~/.ssh/tmaps.pem`` For more information please refer to the `AWS online documentation <http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html#how-to-generate-your-own-key-and-import-it-to-aws>`_.


.. _requirements-software:

Software
--------

On the deploying machine, you need to install the software required for the setup and deployment process.

First, install non-Python dependencies::

    sudo apt-get update
    sudo apt-get -y install git build-essential python-pip python-dev libc6-dev libffi-dev libssl-dev

and then the `tmsetup` Python package::

    git clone https://github.com/TissueMAPS/elasticluster
    cd ~/elasticluster && sudo pip install -e .

    git clone https://github.com/TissueMAPS/TmSetup.git ~/tmsetup
    cd ~/tmsetup && sudo pip install -e .

.. warning:: With older Python versions (such as the 2.6.7 default on Ubuntu 14.04) you may run into SSL problems.

.. _configuration:

Configuration
=============

The setup and deployment process is configured via the ``~/.tmaps/setup/setup.yml`` file.

The file is in `YAML <http://yaml.org/>`_ format has two main sections:

- **cloud**: provides information about the cloud on which `TissueMAPS` should be set up. Currently, three providers are supported:
    + ``os``: `OpenStack <http://www.openstack.org/>`_
    + ``ec2``: `Elastic Compute Cloud (Amazon Web Services) <https://www.s3it.uzh.ch/en/scienceit/infrastructure/sciencecloud.html>`_
    + ``gce``: `Google Compute Engine <https://cloud.google.com/compute/>`_

- **grid**: describes the computational resources that should host `TissueMAPS` and how they need to be configured via `Ansible playbooks <http://docs.ansible.com/ansible/playbooks.html>`_. The different components (web server, database server, ...) may all run on a single machine or get distributed across several dedicated machines. For consistency, the term ``cluster`` is used to refer to a set of machines that needs to be configured the same way - even if there is only one such machine. Each `cluster` is composed of one or more ``node_types``. The nodes (or `hosts` in `Ansible` terminology) belonging to each `type` get assigned to one or more `Ansible groups <http://docs.ansible.com/ansible/intro_inventory.html#hosts-and-groups>`_.

`Ansible` ``groups`` defined in either `tmsetup <https://github.com/TissueMAPS/TmSetup/tree/master/tmsetup/share/playbooks>`_ or `elasticluster <https://github.com/gc3-uzh-ch/elasticluster/tree/master/elasticluster/share/playbooks>`_ playbooks are directly available without the need to specify the path to the respective playbook. Additional custom playbooks can be provided for a group via the ``playbook`` key.

For more details on the individual sections of the setup file, please refer to the documenation of the :mod:`tmsetup.config <tmsetup.config>` module.

In the following, we will walk you through the setup and deployment process for the ``gce`` provider. The procedure is the same for the other cloud providers, but variables need to be adjusted (names of images, machine type flavors, etc).

.. note:: The *tm_setup* script uses an *SSH* ``ProxyCommand`` to connect to remote hosts within the private network via a *bastion host*. This creates problems with the Ansible `become_user <http://docs.ansible.com/ansible/become.html#becoming-an-unprivileged-user>`_ module. To workaround this issue, you need to set ``allow_world_readable_tmpfiles = True`` in the ``/etc/ansible/ansible.cfg`` file.

.. _single-node-setup:

Single-node setup
-----------------

.. figure:: ./_static/singlenode.png
   :width: 75%
   :align: left

   Standalone setup.

   All components (web server, database server, etc) are hosted on the same machine. The instance has a public IP and is accessible via the internet.

To setup a standalone instance, we need to launch only one VM, but then configure it such that it hosts all required `TissueMAPS` components.


The following `Ansible` ``groups`` (defined in the `tmsetup` package) must be assigned to the node:

    - ``tissuemaps_web``
    - ``tissuemaps_compute``
    - ``tissuemaps_database_master``
    - ``tissuemaps_database_worker``

The `TmSetup` repository provides `templates <https://github.com/TissueMAPS/TmSetup/tree/master/etc>`_ for the different cloud providers. Copy the template for your provider to ``~/.tmaps/setup/setup.yml`` on your deploying machine and modify it according to your needs (here exemplified for the `Google Compute Engine (GCE) <https://cloud.google.com/compute/>`_ provider)::

    mkdir -p ~/.tmaps/setup
    cp ~/tmsetup/src/etc/singlenode_setup_gce.yml ~/.tmaps/setup/setup.yml

The template file has the following content:

.. literalinclude:: ./../src/tmsetup/etc/singlenode_setup_gce.yml
   :language: yaml
   :lines: 3-

Replace ``XXX`` with the password that you would like to use for the database. To further customize the setup, you can overriding default values for group variables. For details on available variables, please refer to the documentation of the corresponding `Ansible` playbook and/or role in the `tmsetup` package.

The provided template sets up a machine with 4 CPU cores and 3.75 GB of RAM per virtual CPU and creates a seprate storage volume of 500GB size. Depending on your needs you may want to choose a different `machine type <https://cloud.google.com/compute/docs/machine-types>`_ and/or adapt the volume size. Note that when you omit the ``volume_size`` variable, no additional volume will be used and only the boot disk will be available.

.. note:: The resulting virtual machine instance will have the name ``tissuemaps-standalone-server-001``. This naming convention seems a bit of an overkill for a single server. However, it becomes useful when building a large grid composed of multiple `clusters` with different `types` of nodes. For consistency, we stick to this naming conventing also for the single-node use case.

.. tip:: You can reuse variables using `YAML node anchors and aliases <http://yaml.org/spec/1.2/spec.html#id2785586>`_ (``&`` and ``*``)::

        foo: &foo bla bla

        bar: *foo

.. _multi-node-setup:

Multi-node setup
----------------

.. figure:: ./_static/multinode.png
   :width: 75%
   :align: left

   Grid setup.

   The different components (web server, database server, etc) run on dedicated machines and compute and storage resources are distributed accross multiple nodes. All machines are part of a virtual private cloud. The machine hosting the web server has a public IP and can be accesssed via the internet. The other *compute* and *storage* machines have private IPs and are only accessible from within the grid. In addition, to the required components, a monitoring system will be installed, which provides users a web-based interface to monitor each each node of the grid. The monitoring server is therefore also accessible via the web.

To setup a `TissueMAPS` grid, additional ``cluster`` components are required. These additional components are configured via playbooks provided by `Elasticluster <http://gc3-uzh-ch.github.io/elasticluster/>`_. The individual components and the corresponding `Ansible` ``groups`` are described in more detail below.

.. literalinclude:: ../src/tmsetup/etc/multinode_setup_gce.yml
   :language: yaml
   :lines: 4-


Each of the `cluster` components is open-source and works on all implemented cloud providers:

* `PostgreSQL <https://www.postgresql.org/>`_ database:

  `PostgreSQL` is an open-source object-relational database system. It provides via the `Postgis <http://www.postgis.net/>`_ extension support for geographic objects and enables powerful spatial queries. `TissueMAPS` makes extensive use of `Postgis`. This component can therfore not be exchanged by alternative database systems.

  Ansible groups (`tmsetup` package):

    - ``tissuemaps_database``: assigned to node that runs the `PostgreSQL` server

  .. note:: We have also tested the `PostgresXL <http://postgresxl.org/>`_ cluster as an attempt to scale out the database. However, we were not satisfied with its performance and stability. `Citus <https://docs.citusdata.com/en/v5.2/aboutcitus/what_is_citus.html>`_ represents an intersting cluster alternative. However, `citusdb` doesn't support all `SQL` features (e.g. multi-statement transactions). Using it would require changes in `TissueMAPS`'s API as well as database schema and will complicate further development. As of version 9.6 `PostgreSQL` allows parallelization of (select) queries over CPUs. In our experience, this already gives very good performance even with hundreds of compute nodes concurrently performing selects/inserts.

* `GlusterFS <https://www.gluster.org/>`_ cluster that serves a distributed filesystem for web and compute nodes:

  `GlusterFS` is an open-source scalable network file system, where storage is distributed over multiple servers. In principle, alternative proprietary storage solutions, such as `BeegFs <http://www.beegfs.com/content/>`_ or `Amazon Elastic File System <https://aws.amazon.com/efs/>`_, could be used as a replacement.

  Ansible groups (`elasticluster` package):

    - ``glusterfs_server``: assigned to nodes that run the `GlusterFS` server
    - ``glusterfs_client``: assigned to compute nodes that need to access the filesystem

* `Slurm <http://slurm.schedmd.com/>`_ cluster to run batch compute jobs:

  `Slurm` is an open-source job scheduler and workload manager typically used on classical supercomputers and compute clusters. In principle, `Slurm` could be exchanged by any other workfload manager (e.g. `LSF <http://www-03.ibm.com/systems/spectrum-computing/products/lsf/index.html>`_ or `Torque <http://www.adaptivecomputing.com/products/open-source/torque/>`_) as long as it is supported by `GC3Pie <https://gc3pie.readthedocs.io/en/master/users/configuration.html#resource-sections>`_.

  Ansible groups (`elasticluster` package):

    - ``slurm_master``: assigned to node that runs the `TissueMAPS` web server
    - ``slurm_workers``: assigned to compute nodes

  .. note::  We have implemented fair `scheduling <http://slurm.schedmd.com/sched_config.html>`_, based on `SLURM accounts <http://slurm.schedmd.com/accounting.html>`_. To enable this functionality, create an account for each `TissueMAPS` user using the provided ``create_slurm_account.sh`` script.
..

  .. tip:: Since we may want houndreds of slurm worker nodes, it is advisable to use a pre-built image to speed up the cluster deployment process. To this end, configure a dedicated machine with only the ``tissuemaps_compute`` group and create a `snapshot <https://en.wikipedia.org/wiki/Snapshot_(computer_storage)>`_ of the configured instance. The thereby created image can then be reused to quickly boot additional machines for a scale-out cluster setup.
  
  To create a custom compute image, create an `Ansbile` host file, e.g. ``~/.tmaps/setup/compute-image.yml``, that describes the instance setup (here exemplified for the `Google Compute Engine`):
  
  .. code-block:: ini
  
      tissuemaps-compute-image
  
      [tissuemaps_compute]
      tissuemaps-compute-image
  
      [tissuemaps_compute:vars]
      provider=gce
      image=ubuntu-1404-trusty-v20161020
      flavor=n1-standard-1
      region=us-west1-b
      security_groups=default
      assign_public_ip=no
      network=default
      key_name=tmaps
      ansible_user=ubuntu
      ansible_ssh_private_key_file=~/.ssh/tmaps
  
  Launch the instance::
  
      ansible-playbook -v -i ~/.tmaps/setup/compute-image.yml ~/tmsetup/tmsetup/share/playbooks/instance.yml
  
  and configure it (replace ``XXX`` with IP address that got assigned to the instance)::
  
      ansible-playbook -v -i ~/.tmaps/setup/compute-image.yml ~/tmsetup/tmsetup/share/playbooks/compute.yml -e ansible_host=XXX
  
  When you create a snapshot of the instance, you can use the generated ``image`` in ``~/.tmaps/setup/setup.yml`` and leave out the ``tissuemaps_compute`` group.

* `Ganglia <http://ganglia.info/>`_ monitoring system (optional):

  `Ganglia` is an open-source monitoring system for multi-node high-performance computating systems. It provides a use web inteface that allows users to conveniently monitor workloads on the different cluster components and individual nodes of the grid.

  Ansible groups (`elasticluster` package):

    - ``ganglia_master``: assigned to node that runs the `Ganglia` server
    - ``ganglia_client``: assigned to every node of the grid

* `Hadoop YARN <https://hadoop.apache.org/docs/r2.7.2/hadoop-yarn/hadoop-yarn-site/YARN.html>`_ cluster to run map-reduce compute jobs (optional):
  
  `Apache Spark <http://spark.apache.org/docs/latest/running-on-yarn.html>`_ is an open-source cluster-computing framework with in-memory processing. `Spark` applications can run with different types of `cluster managers <http://spark.apache.org/docs/latest/cluster-overview.html>`_. `TissueMAPS` uses the `YARN` resource manager for interactive data analysis tools when configured with ``tools_library=spark`` and ``spark_master=yarn-client``.

  Ansible groups (`elasticluster` package):

    - ``spark_master``: assigned to node that runs the `YARN` ResourceManager
    - ``spark_worker``: assigned to nodes that run the `YARN` NodeManager

  .. note:: Tool jobs using the `spark` library get submitted to the `SLURM` cluster via `spark-submit <http://spark.apache.org/docs/latest/submitting-applications.html>`_. The `SLURM` worker nodes serve as `YARN clients <http://spark.apache.org/docs/latest/running-on-yarn.html>`_ and drive the computation on the remote `YARN` cluster. The `SLURM` "detour" is done because `Spark` jobs are not fully asynchronous, but require a driving process holding a connection to the cluster. `SLURM` conveniently schedules these jobs and allocates defined resources to these processes. To this end, each `SLURM` workder node must have a copy of the `Hadoop configuration files <https://hadoop.apache.org/docs/r1.2.1/cluster_setup.html#Configuration+Files>`_. These files can be downloaded from the `YARN` cluster. The IP address of the `YARN` resource manager, from where the files can be obtained, can be provided via the ``yarn_master_host`` variable. Not that the deploying must be able to connect to this node via `SSH`.


.. _setup:

Setup
=====

The `tm_setup` program automates setup and configuration of the different ``cluster`` components. The program launches and configures VM instances as specified in each ``cluster`` section using `Ansible <https://www.ansible.com/>`_.

To connect to the cloud, the program requires your credentials, which must be provided via the following provider-specific environment variables:

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

It can be convenient to place these variables into a ``~/.credentials.sh`` file:

.. code-block:: bash

    export GCE_PROJECT=XXX
    export GCE_EMAIL=XXX
    export GCE_CREDENTIALS_FILE_PATH=XXX

and source the file prior to running ``tm_setup``::

    . ~/.credentials.sh

If you forget to set a variable, ``tm_setup`` will remind you.

Setting up the computational infrastructure is then as simple as calling::

    tm_setup -v launch

The ``launch`` command calls the `instance.yml <https://github.com/TissueMAPS/TmSetup/blob/master/tmsetup/share/playbooks/instance.yml>`_ playbook, which launches all instances configured in ``~/.tmaps/setup/setup.yml``.

.. tip:: You can monitor the setup process via the console of your cloud provider, where the created instances (should) appear.

.. note:: Of course, you can also create the virtual machine instance(s) manually via the web console. Keep in mind, however, that you also need to upload keys and create volumes, networks, routers, etc.

.. note:: Virtual machine instances can be terminated via the ``terminate`` command. However, created networks and security groups won't get deleted under the assumption that you may want to use them again.

.. warning:: A private network and security group (firewall) rules will automatically be created based on the provided setup description. Only machines tagged with "web" will be get a public IP and can be directly accessed via *SSH*. The other machine are only accessible from within the private network.

.. _deployment:

Deployment
==========

Once VMs are launched, the `TissueMAPS` application (and potentially other cluster components) can be deployed. This can be achieved with the following command::

    tm_setup -v deploy

The ``deploy`` command calls the following two playbooks:

    - `site.yml <https://github.com/gc3-uzh-ch/elasticluster/blob/master/elasticluster/share/playbooks/site.yml>`_ of the `elasticluster` package: deploys the cluster components and wires everything together
    - `site.yml <https://github.com/TissueMAPS/TmSetup/blob/master/tmsetup/share/playbooks/site.yml>`_ playbook of the `tmsetup` package: deploys the `TissueMAPS` application and the database

Additional playbooks may be called in case you provided any via the ``playbook`` variable.

The resulting grid is configured such that it will automatically start all the servers upon booting. The web-based user interface can be accessed by pointing your web browser to the IP address of the instance hosting the web server.

.. note:: `TissueMAPS` code is installed in editable mode. Local code changes will thus become immediatly effictive.

.. tip:: If you want to share your instance with others, you can make use of the ``tm_users`` variable. Simply list the `Github` user names of people you would like to provide access to and their public `SSH` keys will automatically be downloaded form `Github` and included in ``authorized_hosts``.


