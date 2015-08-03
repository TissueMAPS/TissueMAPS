Main TissueMAPS website
=======================

0. Create account
-----------------

1. Login
--------

User has to login with a username and password. Consider using gmail or facebook usernames.

Tools:

- `Flask-JWT <https://pythonhosted.org/Flask-JWT/>`_

IlUI app
========

2. Register experiment
----------------------

User has to specify name of the experiment and subexperiments (if present).

The information provided by the user is stored in the database.


3. Upload files
---------------

User can upload channel images, i.e. the images acquired on the microscope.

Potentially useful tools:

- `angular-file-upload <https://github.com/nervgh/angular-file-upload>`_

- `Flask-Uploads <https://pythonhosted.org/Flask-Uploads/>`_, see also `uploading files with flask <http://flask.pocoo.org/docs/0.10/patterns/fileuploads/>`_


4. Get file metadata
--------------------

We try to automatically retrieve the required metadata from the xml attached to the image via `python-bioformats <https://pypi.python.org/pypi/python-bioformats/1.0.0>`_,
see `extract metadata <http://pythonhosted.org/python-bioformats/#metadata>`_. If the metadata is not sufficient or is not accessible, the user has to provide the missing information.

The user should be able to provide this information in an interactive way,
optimally by simply modifying a grid of thumbnail images via sliders for the two axes until all images are in the correct position.


5. Create "channel" pyramids
----------------------------

User needs to specify the channels for which he would like to create a pyramid for and the preprocessing options, i.e. whether he wants images to be illumination corrected and shifted.

If the user chooses one of the preprocessing options, the corresponding preprocessing tasks (`corilla` and `align` packages) have to be submitted prior the submission of the actual pyramid creation.


JtUI app
========

6. Create label images and dataset via Jterator (optional)
----------------------------------------------------------

User has to set up a Jterator pipeline (standard pipelines are provided). The pipeline needs to output the segmentation files (label images) and the measured features and positional metadata (object ids, border ids, centroids).

Postprocessing tasks such as data fusion (`dafu` package) has to be done after successful completion and will create the final dataset used by TissueMAPS.

Jterator doesn't output the segmentation images directly, but rather stores the outline coordinates of objects in the HDF5 file (this saves quite some storage). The actual images could be created during the data fusion step if necessary, but optimally the pyramid creation step (`illuminati` package) would directly work with the outlines.

Alternatively, the user can upload the segmentation image files, containing binary mask images. Then he has to use Jterator to generate data and metadata. For now, we won't support upload of user data, because it then gets difficult to ensure a correct mapping of data points in the dataset and objects in the mask pyramid.


7. Create "mask" pyramids (optional)
------------------------------------

User needs to specify the name of the objects for which he would like to create a pyramid. The LUTs and global id pyramids should then automatically be created as well.


GC3Pie
======

We differentiate between temporary and persistent computational jobs:

- **temporary** jobs are all computational requests coming from the main TissueMAPS app, such as clustering or classification tasks, or running a pipeline for an individual *job* via the JtUI app. These tasks fall under the umbrella terms exploratory data analysis and testing. The corresponding jobs are only monitored while the user is logged in and their status is returned to the user via an open websocket connection. If the user logs out while the job is still running he won't be able to retrieve the output at a later time (and the job can be killed). These jobs represent a single *Application* or *ParallelTaskCollection* instance and are thus simple to handle.

- **persistent** jobs are computational requests coming from the IlUI app, such as pyramid creation, as well as submission of pipelines via the JtUI app (note the difference to running a pipeline for one or more individual jobs). These jobs should be monitored even if the user logs out and their status should be saved in the database. The user should be able to retrieve the output of the job at any time when he logs in again (and he should be notified via email and provided a link once the job is terminated). These jobs can be bundeled as a *SequentialTaskCollection* (steps 5-7: preprocessing, data generation via *JtUI*, postprocessing, and pyramid creation via *illuminati*) with dependencies and are thus more complicated to handle. These workflows should in the future be handled by *brainy* and the *brainyUI* app.

