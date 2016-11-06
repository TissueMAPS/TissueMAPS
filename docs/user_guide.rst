**********
User guide
**********

`TissueMAPS` uses the `client-server model <https://en.wikipedia.org/wiki/Client%E2%80%93server_model>`_. Clients make request to the server via a `REST API <http://rest.elkstein.org/2008/02/what-is-rest.html>`_ using the `Hyperstate Transfer Protocol (HTTP) <https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_.

Most users will interact with the server via the browser-based interface. However, additional `HTTP` client implementations are provided via the `tmclient` package, which allows users to interact more programmatically with the server.

The server handles client request, but generally delegates the actual processing to the `tmlibrary` package. The library provides active programming (`API`) and command line interfaces (`CLI`), which can also be used directly, i.e. in a sever independent way.

.. _user-interace:

User interface
==============

.. _user-interface-login:

Login
-----

When you enter the IP address of the web server in your browser (in this demo ``localhost:8002``), you get directed to the *index* site and prompted for login credentials.

.. figure:: ./_static/ui_login.png
   :width: 75%
   :align: center

   Login prompt.

   Enter username and password into the provided forms.

.. _user-interface-userpanel:

Userpanel
---------

After successful authorization, you will see an overview of existing experiments.

.. figure:: ./_static/ui_experiment_list_empty.png
   :width: 75%
   :align: center

   Experiment overview.

   Empty list because no experiments have been created so far.

To create a new :class:`experiment <tmlib.models.experiment.Experiment>`, click on |create_new_exp_button|.

.. figure:: ./_static/ui_experiment_create.png
   :width: 75%
   :align: center

   Experiment creation.

   Provide information about the image acquisition process of the experiment.

When you click on |create_exp_button|, the experiment gets created and you get directed back to the overview.

.. figure:: ./_static/ui_experiment_list_one.png
   :width: 75%
   :align: center

   Experiment overview.

   The created experiment is listed.

Next, you can upload images and process them. To this end, click on |modify_button|, which directs you to the workflow manager.

.. figure:: ./_static/ui_workflow.png
   :width: 75%
   :align: center

   Workflow manager.

   Interface for uploading and processing images. At the top of the page there is a button for *upload* and one for each stage of the :ref:`canonical workflow <canonical-workflow>`.

To begin with, add a new :class:`plate <tmlib.models.plate.Plate>`, by clicking on |create_plate_button|.

.. figure:: ./_static/ui_plate_create.png
   :width: 75%
   :align: center

   Plate creation.

   Provide a name and optionally a description for the plate.

.. figure:: ./_static/ui_plate_list_one.png
   :width: 75%
   :align: center

   Plate overview.

   The created plate is now listed. It is not yet ready for processing, because it doesn't contain any acquisitions yet.

Select the created plate, by clicking on the link |plate_link|.

.. figure:: ./_static/ui_acquisition_list_empty.png
   :width: 75%
   :align: center

   Acquisition overview.

   Empty list because no acquisitions have been added so far for the selected plate.

Add a new :class:`acquisition <tmlib.models.acquisition.Acquisition>`, by clicking on |create_acq_button|.

.. figure:: ./_static/ui_acquisition_create.png
   :width: 75%
   :align: center

   Acquisition creation.

   Provide a name and optionally a description for the acquistion.

.. figure:: ./_static/ui_acquisition_list_one.png
   :width: 75%
   :align: center

   Acquisition overview.

   The created acquisition is now listed. It has status "WAITING" because no images have yet been uploaded.

.. _user-interface-upload:

Upload
------

Select the created acquisition, by clicking on the link |acq_link|.

.. figure:: ./_static/ui_acquisition_upload.png
   :width: 75%
   :align: center

   Upload.

   Either drag and drop files or folders into the dedicated area or select them from your local filesystem by clicking on |select_files_button|. Then click on |upload_files_button| to start the upload process.

.. figure:: ./_static/ui_acquisition_upload_process.png
   :width: 75%
   :align: center

   Upload in process.

   You can monitor the upload status of individual files.

.. note:: File upload via the user interface works reliable for serveral thousand images. When uploading tens or hundreds of thousands of images, we recomment uploading files via the command line instead. To this end, you can use the ``tm_upload`` tool provided by the :mod:`tmclient` package.

.. warning:: The upload process is interrupted when the page gets reloaded. However, you can simple add the files afterwards again and restart uploading. The server keeps track which files have already been uploaded and won't upload them again.

.. figure:: ./_static/ui_plate_list_one_ready.png
   :width: 75%
   :align: center

   Plate overview.

   The loading bar in the top right corner indicates that the upload was successful and is "TERMINATED". The plate is now ready for processing.

You can add additional acquisitions and plates to the experiments by repeating the steps described above. Once you have uploaded all files, you can continue to process them.

.. _user-interface-workflow:

Workflow
--------


.. |create_new_exp_button| image:: ./_static/ui_create_new_exp_button.png
   :height: 15px

.. |create_exp_button| image:: ./_static/ui_create_exp_button.png
   :height: 15px

.. |modify_button| image:: ./_static/ui_modify_button.png
   :height: 15px

.. |create_plate_button| image:: ./_static/ui_create_plate_button.png
   :height: 15px

.. |plate_link| image:: ./_static/ui_plate_link.png
   :height: 15px

.. |create_acq_button| image:: ./_static/ui_create_acq_button.png
   :height: 15px

.. |acq_link| image:: ./_static/ui_acq_link.png
   :height: 15px

.. |select_files_button| image:: ./_static/ui_select_files_button.png
   :height: 15px

.. |upload_files_button| image:: ./_static/ui_upload_files_button.png
   :height: 15px

.. _restful-api:

RESTful API
===========


.. _command-line-interface:

Command line interface
======================



.. _active-programming-interface:

Active programming interface
============================
