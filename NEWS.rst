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


v0.5.x (*in development*)
=========================

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

Deployment chages
-----------------

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
