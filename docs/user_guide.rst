**********
User guide
**********

`TissueMAPS` uses the `client-server model <https://en.wikipedia.org/wiki/Client%E2%80%93server_model>`_. Clients make request to the server via a `REST API <http://rest.elkstein.org/2008/02/what-is-rest.html>`_ using the `Hyperstate Transfer Protocol (HTTP) <https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_.

Most users will interact with the server via the browser-based interface. However, additional `HTTP` client implementations are provided via the `tmclient` package, which allows users to interact more programmatically with the server.

The server handles client request, but generally delegates the actual processing to the `tmlibrary` package. The library provides active programming (`API`) and command line interfaces (`CLI`), which can also be used directly, i.e. in a sever independent way.

.. _user-interace:

User interface
==============

When you enter the IP address of the web server in your browser (in this demo ``localhost:8002``), you get directed to the *index* site and prompted for login credentials.

.. figure:: ./_static/ui_login.png
   :width: 75%
   :align: center

   Login prompt.

   Enter username and password into the provided forms.

.. _user-interface-user-panel:

User panel
----------

After successful authorization, you will see an overview of your existing experiments.

.. figure:: ./_static/ui_experiment_list_empty.png
   :width: 75%
   :align: center

   Experiment overview.

   Empty list because no experiments have been created so far.

.. _user-interface-add-experiment:

Adding an experiment
^^^^^^^^^^^^^^^^^^^^

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

.. note:: By default, experiments can only be viewed and modified by the user who created them, but they can be shared with other users. However, this functionality is currently only available via the API (see :class:`ExperimentShare <tmlib.models.user.ExperimentShare`).

Next, you can upload images and process them. To this end, click on |modify_button|, which directs you to the workflow manager.

.. _user-interface-workflow-manager:

Workflow manager
----------------

.. figure:: ./_static/ui_workflow.png
   :width: 75%
   :align: center

   Workflow manager.

   Interface for uploading and processing images. At the top of the page there is a button for *upload* and one for each stage of the :ref:`canonical workflow <canonical-workflow>`.

.. _user-interface-workflow-manager-uploading-images:

Uploading image files
^^^^^^^^^^^^^^^^^^^^^

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

.. note:: The upload process will be interrupted when the page gets reloaded. However, you can simply add the files afterwards again and restart uploading. The server keeps track which files have already been uploaded and won't upload them again.

.. figure:: ./_static/ui_plate_list_one_ready.png
   :width: 75%
   :align: center

   Plate overview.

   The loading bar in the top right corner indicates that the upload was successful and is "TERMINATED". The plate is now ready for processing.

You can add additional acquisitions and plates to the experiments by repeating the steps described above. Once you have uploaded all files, you can continue to process them.

.. _user-interface-workflow-manager-processing-images:

Processing images
^^^^^^^^^^^^^^^^^

Once you have uploaded all files, you can proceed to the subsequent processing stages.

.. note:: You are prevented from proceeding until upload is completed. Requesting this information from the server may take a few seconds for large experiments.

.. figure:: ./_static/ui_workflow_stage_one.png
   :width: 75%
   :align: center

   Workflow control panel.

   You can toggle between different stages and steps. The view applies to the currently active combination of stage and step - in this case "image convesion" and "metaextract", respectively.

   The loading bars indicate the progress of workflow, stage and step. They are green by default, but turn red as soon as a single job failed. Above the loading bars, you can see the current processing state (e.g. "SUBMITTED", "RUNNING", or "TERMINATED"). When the currently active stage or step is in state "RUNNING", the cog wheel above the loading bar will also start spinning. The cog will also appear on the stage and step tabs to indicate the state of stages or steps, which are not selected at the moment.

   In the main window you can set "batch" and "submission" arguments to control the partition of the computational task into individual jobs and the allocation of resources for each job, respectively. Upon submission, individual jobs will be listed below the argument section. If required arguments are missing for a stage or step, this will be indicated on the corresponding tab by a minus (visible for the "image analysis" stage). In this case, you cannot submit these stages without providing the missing arguments.

   Since the workflow hasn't been submitted yet, the loading bars are all set to zero and no jobs are listed.

You can click through all stages and steps and set arguments according to your needs. Once you are happy with your settings, you can either |save_button| the settings or |submit_button| the workflow for processing (settings get also automatically saved upon submission).

.. note:: Submission depends on the current view. Only the currently active stage as well as stages to the left will be processed. For example, if you are in stage "image preprocessing" and you click on |submit_button|, only stages "image conversion", "image preprocessing" and "pyramid creation" will be submitted.

.. note:: Arguments ``batch_size`` and ``duration`` depend on each other. The larger the batch, i.e. the more images are processed per compute unit, the longer the job will typically take.

.. note:: Arguements ``cores`` and ``memory`` depend upon the available compute resources, i.e. the number of CPU cores and the amount of RAM available per core. The defauls of 3800MB applies to the default machine type flavor at ScienceCloud at University of Zurich and may need to be adapted for other clouds.

For now, let's submit the workflow from the first stage "image conversion".

.. figure:: ./_static/ui_workflow_stage_one_submitted.png
   :width: 75%
   :align: center

   Workflow submission in progress.

   After submitting the workflow from stage "image conversion", the state of step "metaconfig" switched to "RUNNING" and individual jobs are listed. Some of the jobs are already "TERMINATED", while some are still "RUNNING". Note the cogs on the tabs of the other steps indicating that they have also been submitted for processing.

.. figure:: ./_static/ui_workflow_stage_one_done.png
   :width: 75%
   :align: center

   Workflow submission done.

   All steps of stage "image conversion" have been processed and all jobs have "TERMINATED" sucessfully, noticeable by the fully loaded green bars as well as the green checks on stage/step tabs and individual job items.

.. note:: Once a workflow has been submitted, you can safely close the window or disconnect from the internet, since the jobs are processed remotely on the server in an asynchronous manner.

Once stage "image conversion" is done, you can proceed to any other stage and click on |resume_button|. Alternatively, you could have submitted a further downstream stage in the first place.

For the purpose of this demo, we will proceed to stage "pyramid creation" and resume the workflow.

.. figure:: ./_static/ui_workflow_stage_three.png
   :width: 75%
   :align: center

   Workflow submission resumed.

   After successful termination of stage "image conversion", the workflow has been resumed from stage "pyramid creation", which is currently in state "NEW".

.. note:: Once stage "pyramid creation" is done, you can already view the experiment. However, you won't be able to visualize segmented objects on the map. To this end, you first need to process stage "image analysis".

You can further |resubmit_button| the workflow with modified arguments from any stage afterwards.

The image analysis stage is a bit more complex, therefore we will cover it in a separte section.

.. _workflow-interface-image-analysis-pipeline:

Setting up image analysis pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. figure:: ./_static/ui_workflow_stage_four.png
   :width: 75%
   :align: center

   Image analysis stage.

   Notice the "extra arguments" section, which hasn't been present in any of the other previous stages. You are required to select a "pipeline", which should be processed by the "jterator" step. Since no pipeline has been created so far, the drop-down menue is empty.

To begin with, you need to create a pipeline. To this end, click on |create_pipe_button|. Give the pipeline a descriptive name, here we call it ``test-pipe``.
This will direct you to a separte interface for defining the pipeline.


.. figure:: ./_static/ui_jterator.png
   :width: 75%
   :align: center

   Jterator interface.

   On the left side in the "Available Modules" column, you find all modules implemented in the :mod:`jtmodules` package. "Pipeline Settings" describes the input for the pipeline in form of "channels" and lists modules that have been added to the pipeline. The module "Module Settings" section describes input arguments and expected outputs of the currently selected module.

.. figure:: ./_static/ui_jterator_module_one.png
   :width: 75%
   :align: center

   Pipeline and module settings.

   You can drag and drop modules from the list of available modules into the indicated field in the *pipeline* section and then click on added item to set module parameters. The order of modules in the pipeline can be rearranged by dragging them up or down.

   You can further select *channels* in the *input* section to make them available to the pipeline. Additional *channels* can be removed when neeeded. The selected "channels" become available as an *input* for the selected module.

.. tip:: Images for all *channels* selected in the *input* section will be loaded into memory (for the acquisition site corresponding to the given batch). So remove any channel you don't use in your pipeline to gain performance.

.. figure:: ./_static/ui_jterator_module_one_rename.png
   :width: 75%
   :align: center

   Module renaming.

   A module can be renamed by clicking on the textfield in the respective pipeline item. Enter a new name in the provided field and press enter. Note, that the name in the "Module Settings" column remains unchanged. It continues to refer to the module source file.

.. note:: Names of modules in the pipeline must be unique. When adding the same module twice, it will be automatically renamed by appending it with a number. Be aware that names of module outputs must be hashable and therefore also unique. Best practice is to use to use the module as a namespace: ``<module_name>.<output_argument_name>``, e.g. ``smooth.smoothed_image`` for the above example. Since module names must be unique the resulting *output* will consequently have a unique name, too.

Add all modules to the pipeline that you need for your analysis and set parameters.

.. note:: Types of *input* parameters are checked internally. Only inputs matching the type definition of the *input* argument are listed in the drop-down menue.

Here, we will first add all the modules required to segment "Nuclei" and "Cells" in the images.

.. figure:: ./_static/ui_jterator_module_many_segment.png
   :width: 75%
   :align: center

   Example segmentation pipeline.

   This pipeline identifies primary ("Nuclei") and secondary objects ("Cells"): The image corresponding to channel "wavelength-1" is smoothed and subsequently thresholded. The resulting mask is then labeled to define individual primary objects. The primary objects are subsequently expanded using a watershed transform of the smoothed image belonging to channel "wavelength-2", which generates secondary objects.

The pipeline can be saved at any time by clicking on |save_button|. This will save the pipeline settings as well as settings of each module in the pipeline.

When all required parameters are set, the pipeline can be submitted by clicking on |submit_button| (submission will automatically save the pipeline as well).

.. figure:: ./_static/ui_jterator_submit.png
   :width: 75%
   :align: center

   Pipeline submission.

   Up to ten jobs can be maximally submitted for a pipeline.

To see which acquisition sites the jobs map to, click on |list_jobs_button|.

.. figure:: ./_static/ui_jterator_joblist.png
   :width: 75%
   :align: center

   Job list.

   The table shows the name of "plate" and "well" as well as the "x" and "y" coordinate of each :class:`site <tmlib.models.site.Site>` corresponding to a particular job. This is intended to help you select job IDs for testing your pipeline, such that you include images from different wells or positions within a well.

.. note:: In the workflow panel you can set a ``batch_size`` for the "jterator" step. However, when you submit the pipeline for testing in the jterator user interface, ``batch_size`` will be automatically set to 1, such that only one acquisition :class:`site <tmlib.models.site.Site>` will be processed per job.

Once submitted, jobs get cued and processed depending on available computational resources. If you have access to enough compute units, all jobs will be processed in parallel.

.. figure:: ./_static/ui_jterator_results.png
   :width: 75%
   :align: center

   Pipeline results.

   Results of individual jobs are listed in the "Results" column. |figure_button| is active for the currently selected module.

When clicking on |figure_button|, the figure for the respective job is displayed in fullscreen mode.

.. figure:: ./_static/ui_jterator_figure.png
   :width: 75%
   :align: center

   Module figures.

   Figures are interactive. Pixels values are displayed when hovering over images. You can also zoom into plots to have a closer look. Be aware, however, that plots may have a reduced resolution.

.. note:: Plotting needs to be explicitely activated for a module by selecting ``true`` for argument "plot". This is done to speed up processing of the pipeline.

When clicking on |log_button|, the log output for the respective job is displayed. The messages includes the log of the entire pipeline and is the same irrespective of which module is currently active.

.. figure:: ./_static/ui_jterator_log.png
   :width: 75%
   :align: center

   Pipeline log outputs.

   Standard output and error are caputered for each pipeline run. The logging level is set to ``INFO`` by default.

To save segmented objects and be able to assign values of extracted features to them, objects need to be registered using the :mod:`register_objects <jtmodules.register_objects>` modules. From a user perspective, the registration simply assigns a name to a label image.


.. figure:: ./_static/ui_jterator_object_registration.png
   :width: 75%
   :align: center

   Object registration.

   Assign a unique, but short and descriptive name to each type of segmented objects that you want to save. To this end, objects need to be provided in form of a labled image, where each object has a unique ID, as output by the :mod:`label <jtmodules.label>` module, for example.

When we are happy with the segmentation results, we can add addtional modules for feature extraction.

.. warning:: All extracted features will be automatically saved. Since the resulting I/O will increase processing time, its recommended to exclude *measurement* modules from the pipeline for tuning segmentation parameters.

.. tip:: You can inactivate modules by clicking on |eye_open_symbol| without having to remove them from the pipeline. Just be aware that this may affect downstream modules, since the *output* of inactivated modules will of course no longer be produced.

.. tip:: You can quickly move down and up in the pipeline in a `Vim <http://www.vim.org/>`_-like manner using the *j* and *k* keys, respectively.

.. figure:: ./_static/ui_jterator_feature_extraction.png
   :width: 75%
   :align: center

   Feature extraction.

   Select a previously registerd object type for which you would like to take a measurement. Some features, such as ``intensity`` require an additional raster image. Others, such as ``morphology`` measure only object size and shape and are thus independent of the actual pixel intensity values.

.. note:: Feature names follow a convention: ``<class>_<statistic>_<channel>``. In case features are intensity-independent, the name reduces to ``<class>_<statistic>``. For the above example this would result in ``Intensity_mean_wavelength-2`` or ``Morphology_area``.

Once you have set up your pipeline, save your pipeline (!) and return to the workflow panel. Select the created pipeline and submit the "image analysis" stage by clicking on |resume_button|. In contrast to submissions in the *jterator* user interface, this will now submit all jobs and potentially run more than one pipeline per job in a sequential manner, depending on the specified ``batch_size``.

.. figure:: ./_static/ui_workflow_stage_four_submission.png
   :width: 75%
   :align: center

   Image analysis submission.

   Select the created pipline in the drop-down menu. In case the pipeline doesn't show up, you may have to |reload_button| the workflow settings.


.. _user-interface-viewer:

Viewer
------

Once you've setup your *experiment*, you can view it by returning to the `user panel`_ and clicking on |view_button|.


.. figure:: ./_static/ui_viewer.png
   :width: 75%
   :align: center

   Viewer overview.

   Upon initial access, the first channel is shown in the viewport at the maximally zoomed-out resultion level.
   You can zoom in and out using either the mouse wheel or trackpad or the + and - buttons provided at the top left corner of the viewport.
   The map can also be repositions within the viewport by dragging it with the mouse.

   To the right of the viewport is the map sidebar and to the left the tool sidebar. Sections of the map control sidebar can be resized using the mouse and individual items can be rearranged via drag and drop.
   Below the viewport are sliders to zoom along the *z*-axis or time series for experiment comprised of images acquired at different *z* resolutions or time points, respectively.

The map sidebar has the following sections:

    - ``Channels``: one raster image layer for each channel (created during the "pyramid_creation" workflow stage)
    - ``Objects``: one vector layer for each object type (created during the "image_analysis" workflow stage)
    - ``Selections``: tool for selecting mapobjects on the map
    - ``Saved results``: one vector layer for each saved (previously generated) tool result
    - ``Current result``: single vector layer for the most recent tool result

Individual sections are described in more detail below.

.. figure:: ./_static/ui_viewer_sidebar_channels.png
   :width: 75%
   :align: center

   Map sidebar: Channels.

   Channels are represented on the map in form of raster images. Individual channel layers can be toggled as well as dynamically colorized and rescaled.
   By default, channels are shown in grayscale. When multiple channels are active, colors are additively blended (e.g. red + green = yellow).
   Pixel intensities are mapped to 8-bit for map representation. However, intensities value shown below sliders reflect the original bit range.


.. figure:: ./_static/ui_viewer_sidebar_objects.png
   :width: 75%
   :align: center

   Map sidebar: Objects.

   Objects are represented on the map in form of vector graphics. Individual object layers can be toggled as well as dyncamically colorized. In addition, the opacity of object outlines can be adapted. When multiple objects are active, colors are additively blended.

.. note:: Objects of type "Plates", "Wells" and "Sites" will be auto-generated based on available image metadata. These *static* types are independent of parameters set in the "image_analysis" workflow stage.

.. warning:: Object outlines may not be represented 100% accurately on the map, because the polygon contours might have been simplified server side.

.. figure:: ./_static/ui_viewer_sidebar_selections.png
   :width: 75%
   :align: center

   Map sidebar: Selections.

   Objects can be selected and assigned to different groups. A map marker will be dropped at each selected object. An object can be unselected by clicking on it again using the same selection item. More than one marker can be assigned to an object.
   The respective object layer will automatically be activated for the choosen mapobject type.


Selections can subsequently be used by tools. For example, to perform supervised classification using the "SVC" tool.

.. figure:: ./_static/ui_viewer_tools_example.png
   :width: 75%
   :align: center

   Tool sidebar.

   Each tool is associated with a separate window, which opens when the corresponding tool icon is clicked in the tool sidebar.

   The window content varies between tools depending on their functionality. Typically, there is a section for selection of object types and features and a button to submit the tool request to the server.
   In case of the supervised classification (SVC) tool, there is also a section for assigning selections to label classes, which can be used for training of the classifier.

To perform the classification, click on |classify_button|. This will submit a request to the server to perform the computation. Once the classification is done the result will appear in the "Current result" section of the map control sidebar.

.. figure:: ./_static/ui_viewer_sidebar_current_result.png
   :width: 75%
   :align: center

   Map sidebar: current result.

   Once a tool result is available a layer will appear in the "Current result" section. Similar to object layers, they are represented on the map as vector graphics. In contrast to the object layers, however, the filled objects are shown instead outlines. Result layers can also be toggled and the opacity can be changed to reveal underlying channel layers (or other tool result layers).


.. figure:: ./_static/ui_viewer_sidebar_saved_results.png
   :width: 75%
   :align: center

   Map sidebar: saved results.

   When additional tool requests become available, the "Current result" moves to "Saved results" and gets replaced with the more recent result. Multiple results can be active simultaneously and their colors are additively blended. Transparency of result layers can be controlled independently. Here, we performed an additional unsupervised classification, using the same features and number of classes, and can now compare the results of the supervised with the unsupervised analysis on the map.


.. |create_new_exp_button| image:: ./_static/ui_create_new_exp_button.png
   :height: 15px

.. |create_exp_button| image:: ./_static/ui_create_exp_button.png
   :height: 15px

.. |modify_button| image:: ./_static/ui_modify_button.png
   :height: 15px

.. |view_button| image:: ./_static/ui_view_button.png
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

.. |submit_button| image:: ./_static/ui_submit_button.png
   :height: 15px

.. |classify_button| image:: ./_static/ui_classify_button.png
   :height: 15px

.. |resume_button| image:: ./_static/ui_resume_button.png
   :height: 15px

.. |reload_button| image:: ./_static/ui_reload_button.png
   :height: 15px

.. |resubmit_button| image:: ./_static/ui_resubmit_button.png
   :height: 15px

.. |save_button| image:: ./_static/ui_save_button.png
   :height: 15px

.. |create_pipe_button| image:: ./_static/ui_create_pipe_button.png
   :height: 15px

.. |list_jobs_button| image:: ./_static/ui_list_jobs_button.png
   :height: 15px

.. |figure_button| image:: ./_static/ui_figure_button.png
   :height: 15px

.. |log_button| image:: ./_static/ui_log_button.png
   :height: 15px

.. |eye_open_symbol| image:: ./_static/ui_eye_open_symbol.png
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
