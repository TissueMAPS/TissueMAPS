--------------------------------------
 User-visible changes across releases
--------------------------------------

.. This file follows reStructuredText markup syntax; see
   http://docutils.sf.net/rst.html for more information

.. highlights::

  This is a list of user-visible changes worth mentioning: new
  features, backwards-incompatible changes, and important bug fixes.

  In each new release, items are added to the top of the file and
  identify the version they pertain to.  TissueMAPS follows the
  `semantic versioning`_ scheme; only the first two components
  (*major* and *minor* version) are used in this document, and all the
  changes in the same major+minor release series are lumped together.

.. _`semantic versioning`: https://semver.org/

.. NOTE TO AUTHORS:

  Don’t discard old items; leave them in the file after the newer
  items. This way, a user upgrading from any previous version can see
  what is new.

  See also: https://www.gnu.org/prep/standards/html_node/NEWS-File.html
  (from whence the above quote was taken)


.. contents::


v0.6.0
======

Feature addition release; note that the `tm_client Python package on pypi`_
hasn't been updated since TM v0.3.3 (October 2017), similarly to the
`TissueMaps docker image`_ (August 2017).

.. _`tm_client Python package on pypi`: https://pypi.org/project/tmclient/
.. _`TissueMaps docker image`: https://hub.docker.com/r/tissuemaps/


New features
------------

* Add experiment list ordering capability, by Joel Luehti (`PR #2 on pelkmanslab/TissueMAPS`_)
* Save training labels of classifiers, by Joel Luehti (`PR #4 on pelkmanslab/TissueMAPS`_)

.. _`PR #2 on pelkmanslab/TissueMAPS`: https://github.com/pelkmanslab/TissueMAPS/pull/2
.. _`PR #4 on pelkmanslab/TissueMAPS`: https://github.com/pelkmanslab/TissueMAPS/pull/4


v0.5.x
======

The minor version change is warranted by the many changes on the
deployment side (basically, the Ansible playbooks were completely
rewritten); little has changed however on the side of TM
functionality.

New features
------------

* New module ``use_label_image`` to import segmentation images
  produced by external utilities (e.g. CellProfiler)

Deployment changes
------------------

* Allow deploying TissueMAPS as an arbitrary user.
* Only read one GC3Pie configuration file. Environmental variable
  ``GC3PIE_CONF`` takes precendence; otherwise the default
  ``~/.gc3/gc3pie.conf`` is used.
* Set PostGreSQL-related env vars. So that running `psql` when
    TissueMAPS' environment is loaded connects you to the relevant DB.
* ``tm_deploy``: Do *not* grant SSH port access to the world.
    SSH access should be only granted to the admin's computers through the
    "default" security group (or any other security group that can be
    added to the VMs).
* ``tm_deploy``: Allow selecting Git repo and branch for TissueMAPS sources.
* Consolidate requirements for all packages into a single
  ``requirements.txt`` file. Only ``tmclient/`` and ``tmdeploy/`` keep
  their own requirements lists, since they are more likely to be
  installed independently of the server code.

Important bug fixes
-------------------

* ``tm_client``: Raise error if path for acquisition dir registration is invalid.
* Fix order of x and y coordinates in centroid (#173), thanks to @scottberry
* Improved separate clumps module (#170), thanks to Joel Luehti
* Protect against non-consecutive labels in label image (#168), thanks to @scottberry
* Fix ``IndexError`` in computing morphology features. Occasionally,
  ``skimage.regionprops`` will not compute features for a certain
  labelled object.  In this case, fill the corresponding row with
  NaN's.
* Use ``yaml.safe_load()`` instead of insecure ``yaml.load()``. This
  silences the warnings that newer versions of PyYAML emit when
  ``yaml.load()`` is used with the default loader.
* Raise memory limit for "init" and "collect" jobs to 2500MB.  Having
  a hard-coded limit independent of experiment size is still a bug,
  but at least the new limit seems to be fine in most cases found so
  far at the Pelkmans Lab.


v0.4.3
======

New features
------------

* Jterator's `measure_morphology` module now provides centroid
  location and all features computed by scikit-image's `regionprops()`
  function (thanks to @scottberry)
* Improvements to Jterator's `separate_clumps` module, in particular:
  change the "separate clumps" procedure to 8-connectivity to avoid
  loss of nuclei, and improve selection test mode (thanks to @jluethi)
* New `mapobject exhibit` command to display the neighborhood of a
  given mapobject with segmentation countours overlaid (thanks to
  Micha Mueller)

Deployment changes
------------------

There are a number of changes in the way TissueMAPS is deployed by `tm_deploy`:

* All TM processes are now managed by `supervisord`. Hence, commands
  to (re)start and stop the TM daemons are now::

    sudo supervisorctl start tm_server # or: tm_jobdaemon
    sudo supervisorctl start tm_server # or: tm_jobdaemon

* HTTPS is no longer enabled at all.  While this is contrary to
  current web deployment best practices, no-one was really using it
  (because the playbooks did not deploy a valid certificate) and even
  getting a valid verifiable certificate can be tricky for private
  installations.  HTTPS support will be reinstated when the code is
  more stable and we are going to go public.
* NginX is no longer needed, now all HTTP serving is handled by uWSGI.
* PostGreSQL 11 is now installed by default.


v0.4.2
======

New features
------------

* `identify_primary_iterative` module from (Pelkmans' Lab fork of
  CellProfiler 1.x) is now available as a Jterator module (thanks to
  @scottberry)

Important bug fixes
-------------------

* Workflow resubmission is again possible, with the same semantics it
  used to have before release 0.4.0 (#118)
* Source code of Jterator modules can be viewed online again (#102)
  and the module name is correct (#101).


v0.4.1
======

Incompatible changes
--------------------

* All TissueMAPS-related sources have been merged in the single
  repository http://github.com/TissueMAPS/TissueMAPS/ This does
  not introduce incompatibilities for end-users, but is an important
  change for developers.


v0.4.0
======

Incompatible changes
--------------------

* JtLibrary and JtModules have been merged into the single repository
  http://github.com/TissueMAPS/JtLibrary/ This change affects all
  users developing their own Jterator modules.

New features
------------

* tm_client: New "register" feature to make the TM server read files
  from a directory, without the need to upload/copy them. (Contributed
  by @sparkvilla)
* tm_client: New option to convert files to PNG during upload.
* tm_client: Allow parallel uploads of files, to maximize bandwidth
  utilization.
* Handling of jobs has now been split off to a separate "job daemon"
  process.  This allows better logging and fixes some concurrency
  issues.
* tm_deploy: Allow the ``tissuemaps`` user to run ``sudo service uwsgi
  start/stop/restart``, so the server can be restarted without logging
  in as a different user.
* Allow configuring the validity time of the JWT authorization token;
  by default set it to 72 hours (was: 6) to allow using one token for
  large dataset uploads in one single ``tm_client`` invocation.

Important bug fixes
-------------------

* The "Kill" button in the web interface works.
* tm_deploy: Ensure that GC3Pie is configured with correct memory
  limits given the features of the compute nodes available.
* tm_client: Retry upload upon failure.
* Make Jterator jobs run correctly on JVM 8+.
* Allow file names up to 256 characters.


.. template new entry:

   vX.Y
   ====

   Incompatible changes
   --------------------

   No incompatibility with the previous releases is expected.

   New features
   ------------

   No new features have been added.

   Important bug fixes
   -------------------

   No important bugs have been fixed.
