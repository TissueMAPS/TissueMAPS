# Copyright 2016 Markus D. Herrmann, University of Zurich
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse

def _check_dependency(required_arg, required_value=None):
    class ArgumentDependencyAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            if getattr(namespace, required_arg) is None:
                parser.error(
                    'Argument "--%s" also requires "--%s".' % (
                        self.dest, required_arg
                    )
                )
            if required_value is not None:
                if getattr(namespace, required_arg) != required_value:
                    parser.error(
                        'Argument "--%s" can only be used when value of '
                        '"--%s" is %s.' % (
                            self.dest, required_arg, str(required_value)
                        )
                    )
            setattr(namespace, self.dest, values)
    return ArgumentDependencyAction


parser = argparse.ArgumentParser(
    prog='tm_client', description='TissueMAPS REST API client.'
)
parser.add_argument(
    '-H', '--host', required=True,
    help='name of TissueMAPS server host'
)
parser.add_argument(
    '-P', '--port', type=int, default=80,
    help='number of the port to which the server listens (default: 80)'
)
parser.add_argument(
    '-u', '--user', dest='user_name', required=True,
    help='name of TissueMAPS user'
)
parser.add_argument(
    '-p', '--password',
    help='password of TissueMAPS user'
)
parser.add_argument(
    '-v', '--verbosity', action='count', default=0,
    help='increase logging verbosity'
)
parser.add_argument(
    '-e', '--experiment', dest='experiment_name', required=True,
    help='name of the experiment that should be accessed'
)

subparsers = parser.add_subparsers(
    dest='resources', help='resources'
)
subparsers.required = True

###################
# Abstract parser #
###################

abstract_plate_parser = argparse.ArgumentParser(add_help=False)
abstract_plate_parser.add_argument(
    '-p', '--plate', dest='plate_name', required=True,
    help='name of the plate'
)

abstract_well_parser = argparse.ArgumentParser(
    add_help=False, parents=[abstract_plate_parser]
)
abstract_well_parser.add_argument(
    '-w', '--well', dest='well_name', required=True,
    help='name of the well'
)

abstract_site_parser = argparse.ArgumentParser(
    add_help=False, parents=[abstract_well_parser]
)
abstract_site_parser.add_argument(
    '-x', dest='well_pos_x', type=int, required=True,
    help='zero-based x cooridinate of acquisition site within the well'
)
abstract_site_parser.add_argument(
    '-y', dest='well_pos_y', type=int, required=True,
    help='zero-based y cooridinate of acquisition site within the well'
)

abstract_acquisition_parser = argparse.ArgumentParser(
    add_help=False, parents=[abstract_plate_parser]
)
abstract_acquisition_parser.add_argument(
    '-a', '--acquisition', dest='acquisition_name', required=True,
    help='name of the acquisition'
)

abstract_site_parser = argparse.ArgumentParser(add_help=False)
abstract_site_parser.add_argument(
    '-p', '--plate', dest='plate_name', required=True,
    help='name of the plate'
)
abstract_site_parser.add_argument(
    '-w', '--well', dest='well_name', required=True,
    help='name of the well'
)
abstract_site_parser.add_argument(
    '-x', '--well-pos-x', dest='well_pos_x', type=int, required=True,
    help='zero-based x cooridinate of acquisition site within the well'
)
abstract_site_parser.add_argument(
    '-y', '--well-pos-y', dest='well_pos_y', type=int, required=True,
    help='zero-based y cooridinate of acquisition site within the well'
)

abstract_tpoint_parser = argparse.ArgumentParser(
    add_help=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
abstract_tpoint_parser.add_argument(
    '-t', '--tpoint', type=int, default=0,
    help='zero-based time point index'
)

abstract_zplane_parser = argparse.ArgumentParser(
    add_help=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
abstract_zplane_parser.add_argument(
    '-z', '--zplane', type=int, default=0,
    help='zero-based z-plane index'
)

abstract_object_parser = argparse.ArgumentParser(add_help=False)
abstract_object_parser.add_argument(
    '-o', '--object-type', dest='mapobject_type_name', required=True,
    help='name of the objects type'
)

abstract_feature_parser = argparse.ArgumentParser(add_help=False)
abstract_feature_parser.add_argument(
    '-f', '--feature', dest='feature_name', required=True,
    help='name of the feature'
)

abstract_channel_parser = argparse.ArgumentParser(add_help=False)
abstract_channel_parser.add_argument(
    '-c', '--channel', dest='channel_name', required=True,
    help='name of the channel'
)

abstract_name_parser = argparse.ArgumentParser(add_help=False)
abstract_name_parser.add_argument(
    '-n', '--name', required=True, help='name'
)

abstract_new_name_parser = argparse.ArgumentParser(add_help=False)
abstract_new_name_parser.add_argument(
    '--new-name', dest='new_name', required=True, help='new name'
)

abstract_description_parser = argparse.ArgumentParser(add_help=False)
abstract_description_parser.add_argument(
    '--description', default='', help='optional description'
)

abstract_workflow_description_parser = argparse.ArgumentParser(add_help=False)

##############
## Workflow ##
##############

workflow_parser = subparsers.add_parser(
    'workflow', help='workflow resources',
    description='Access workflow resources of the experiment.'
)
workflow_subparsers = workflow_parser.add_subparsers(
    dest='workflow_methods', help='access methods'
)
workflow_subparsers.required = True

###############
# Description #
###############

workflow_description_parser = workflow_subparsers.add_parser(
    'description', help='workflow description resources',
    description='Access workflow description resources.',
)
workflow_description_subparsers = workflow_description_parser.add_subparsers(
    dest='workflow_description_methods', help='access methods'
)
workflow_description_subparsers.required = True

workflow_description_download_parser = workflow_description_subparsers.add_parser(
    'download', help='download the workflow description',
    description='Download the workflow description.'
)
workflow_description_download_parser.add_argument(
    '--file', dest='filename', required=True,
    help='path to file to which workflow description should be written'
)
workflow_description_download_parser.set_defaults(
    method='download_workflow_description_file'
)

workflow_description_upload_parser = workflow_description_subparsers.add_parser(
    'upload', help='upload a workflow description',
    description='Upload a provided workflow description.',
    parents=[abstract_workflow_description_parser]
)
workflow_description_upload_parser.add_argument(
    '--file', dest='filename', required=True,
    help='path to file from which workflow description should be read'
)
workflow_description_upload_parser.set_defaults(
    method='upload_workflow_description_file'
)

#######
# Job #
#######

workflow_job_parser = workflow_subparsers.add_parser(
    'job', help='workflow job resources',
    description='Access workflow job resources.',
)
workflow_job_subparsers = workflow_job_parser.add_subparsers(
    dest='workflow_job_methods', help='access methods'
)
workflow_job_subparsers.required = True

workflow_job_submit_parser = workflow_job_subparsers.add_parser(
    'submit', help='submit the workflow',
    description='Submit the workflow using a previously uploaded description. '
)
workflow_job_submit_parser.set_defaults(method='submit_workflow')

workflow_job_resubmit_parser = workflow_job_subparsers.add_parser(
    'resubmit', help='resubmit the workflow',
    description=(
        'Resubmit the workflow at the given stage using a previoulsy '
        'uploaded description.'
    )
)
workflow_job_resubmit_parser.add_argument(
    '-s', '--stage', dest='stage_name',
    help='name of the stage at which the workflow should be resubmitted'
)
workflow_job_resubmit_parser.set_defaults(method='resubmit_workflow')

workflow_job_kill_parser = workflow_job_subparsers.add_parser(
    'kill', help='kill the workflow',
    description='Kill the workflow.'
)
workflow_job_kill_parser.set_defaults(method='kill_workflow')

workflow_job_status_parser = workflow_job_subparsers.add_parser(
    'status', help='show the status of the workflow',
    description='Show the status of the workflow.'
)
workflow_job_status_parser.add_argument(
    '--depth', default=2, help='querying depth'
)
workflow_job_status_parser.set_defaults(method='_show_workflow_status')


##########
## Data ##
##########

data_parser = subparsers.add_parser(
    'data', help='data resources',
    description='Access data resources of the experiment.'
)
data_subparsers = data_parser.add_subparsers(
    dest='data_models', help='data resource type'
)
data_subparsers.required = True


##############
# Experiment #
##############

experiment_parser = data_subparsers.add_parser(
    'experiment', help='experiment resources',
    description='Access experiment resources.',
)
experiment_subparsers = experiment_parser.add_subparsers(
    dest='experiment_methods', help='access methods'
)
experiment_subparsers.required = True

experiment_rename_parser = experiment_subparsers.add_parser(
    'rename', help='rename the experiment',
    description='Rename the experiment.',
    parents=[abstract_new_name_parser]
)
experiment_rename_parser.set_defaults(method='rename_experiment')

experiment_create_parser = experiment_subparsers.add_parser(
    'create', help='create the experiment',
    description='Create the experiment.',
)
experiment_create_parser.add_argument(
    '--workflow-type', dest='workflow type',
    default='canonical', help='workflow type'
)
experiment_create_parser.add_argument(
    '--microscope-type', dest='microscope_type',
    default='cellvoyager', help='microscope type'
)
experiment_create_parser.add_argument(
    '--plate-format', dest='plate_format',
    type=int, default=384,
    help='well-plate format, i.e. total number of wells per plate'
)
experiment_create_parser.add_argument(
    '--plate-acquisition-mode', dest='plate_acquisition_mode',
    default='basic', choices={'basic', 'multiplexing'},
    help='''
        whether multiple acquisitions of the same plate are interpreted
        as time points ("basic" mode) or multiplexing cycles
        ("multiplexing" mode)
    '''
)
experiment_create_parser.set_defaults(method='create_experiment')

experiment_delete_parser = experiment_subparsers.add_parser(
    'rm', help='delete the experiment',
    description='Delete the experiment.',
)
experiment_delete_parser.set_defaults(method='delete_experiment')


##########
# Plates #
##########

plate_parser = data_subparsers.add_parser(
    'plate', help='plate resources',
    description='Access plate resources.',
)
plate_subparsers = plate_parser.add_subparsers(
    dest='plate_methods', help='access methods'
)
plate_subparsers.required = True

plate_list_parser = plate_subparsers.add_parser(
    'ls', help='list plates',
    description='List plates.'
)
plate_list_parser.set_defaults(method='_list_plates')

plate_rename_parser = plate_subparsers.add_parser(
    'rename', help='rename a plate',
    description='Rename a plate.',
    parents=[abstract_name_parser, abstract_new_name_parser]
)
plate_rename_parser.set_defaults(method='rename_plate')

plate_create_parser = plate_subparsers.add_parser(
    'create', help='create a new plate',
    description='Create a new plate.',
    parents=[abstract_name_parser, abstract_description_parser]
)
plate_create_parser.set_defaults(method='create_plate')

plate_delete_parser = plate_subparsers.add_parser(
    'rm', help='delete a plate',
    description='Delete a plate.',
    parents=[abstract_name_parser]
)
plate_delete_parser.set_defaults(method='delete_plate')


#########
# Wells #
#########

well_parser = data_subparsers.add_parser(
    'well', help='well resources',
    description='Access well resources.',
)
well_subparsers = well_parser.add_subparsers(
    dest='well_methods', help='access methods'
)
well_subparsers.required = True

well_list_parser = well_subparsers.add_parser(
    'ls', help='list wells',
    description='List wells.'
)
well_list_parser.add_argument(
    '-p', '--plate', help='name of a plate'
)
well_list_parser.set_defaults(method='_list_wells')


#########
# Sites #
#########

site_parser = data_subparsers.add_parser(
    'site', help='site resources',
    description='Access site resources.',
)
site_subparsers = site_parser.add_subparsers(
    dest='site_methods', help='access methods'
)
site_subparsers.required = True

site_list_parser = site_subparsers.add_parser(
    'ls', help='list sites',
    description='List sites.'
)
site_list_parser.set_defaults(method='_list_sites')


###############
# Acquistions #
###############

acquisition_parser = data_subparsers.add_parser(
    'acquisition', help='acquisition resources',
    description='Access acquisition resources.',
)
acquisition_subparsers = acquisition_parser.add_subparsers(
    dest='acquisition_methods', help='access methods'
)
acquisition_subparsers.required = True

acquisition_list_parser = acquisition_subparsers.add_parser(
    'ls', help='list acquisitions',
    description='List acquisitions.'
)
acquisition_list_parser.add_argument(
    '-p', '--plate', help='name of a plate'
)
acquisition_list_parser.set_defaults(method='_list_acquisitions')

acquisition_create_parser = acquisition_subparsers.add_parser(
    'create', help='create an acquisition',
    description='Create a new acquisition for an existing plate.',
    parents=[
        abstract_name_parser, abstract_plate_parser,
        abstract_description_parser
    ]
)
acquisition_create_parser.set_defaults(method='create_acquisition')

acquisition_delete_parser = acquisition_subparsers.add_parser(
    'rm', help='delete an acquisition',
    description='Delete an acquisition.',
    parents=[abstract_name_parser, abstract_plate_parser]
)
acquisition_delete_parser.set_defaults(method='delete_acquisition')

acquisition_rename_parser = acquisition_subparsers.add_parser(
    'rename', help='rename an acquisition',
    description='Rename an acquisition.',
    parents=[
        abstract_name_parser, abstract_plate_parser,
        abstract_new_name_parser
    ]
)
acquisition_rename_parser.set_defaults(method='rename_acquisition')


####################
# Microscope files #
####################

microscope_file_parser = data_subparsers.add_parser(
    'microscope-file', help='microscope file resources',
    description='Access microscope file resources.',
)
microscope_file_subparsers = microscope_file_parser.add_subparsers(
    dest='microscope_file_methods', help='access methods'
)
microscope_file_subparsers.required = True

microscope_file_list_parser = microscope_file_subparsers.add_parser(
    'ls', help='list microscope files',
    description='List microscope files.',
    parents=[abstract_acquisition_parser]
)
microscope_file_list_parser.set_defaults(method='_list_microscope_files')

microscope_file_upload_parser = microscope_file_subparsers.add_parser(
    'upload',
    help='upload microscope files',
    description='Upload microscope image and metadata files.',
    parents=[abstract_acquisition_parser]
)
microscope_file_upload_parser.add_argument(
    '--directory', required=True,
    help='path to directory where files are located'
)
microscope_file_upload_parser.set_defaults(
    method='upload_microscope_files'
)


############
# Channels #
############

channel_parser = data_subparsers.add_parser(
    'channel', help='channel resources',
    description='Access channel resources.',
)
channel_subparsers = channel_parser.add_subparsers(
    dest='channel_methods', help='access methods'
)
channel_subparsers.required = True

channel_list_parser = channel_subparsers.add_parser(
    'ls', help='list channels',
    description='List channels.',
)
channel_list_parser.set_defaults(method='_list_channels')

channel_rename_parser = channel_subparsers.add_parser(
    'rename', help='rename a channel',
    description='Rename a channel.',
    parents=[abstract_name_parser, abstract_new_name_parser]
)
channel_rename_parser.set_defaults(method='rename_channel')


###################
# Mapobject types #
###################

object_type_parser = data_subparsers.add_parser(
    'object-type', help='object type resources',
    description='Access object type resources.',
)
object_type_subparsers = object_type_parser.add_subparsers(
    dest='object_type_methods', help='access methods'
)
object_type_subparsers.required = True

object_type_list_parser = object_type_subparsers.add_parser(
    'ls', help='list object types',
    description='List object types.',
)
object_type_list_parser.set_defaults(method='_list_mapobject_types')

object_type_rename_parser = object_type_subparsers.add_parser(
    'rename', help='rename an object type',
    description='Rename an object type.',
    parents=[abstract_name_parser, abstract_new_name_parser]
)
object_type_rename_parser.set_defaults(method='rename_mapobject_type')

object_type_delete_parser = object_type_subparsers.add_parser(
    'rm', help='delete an objects type',
    description='Delete an objects type.',
    parents=[abstract_name_parser]
)
object_type_delete_parser.set_defaults(method='delete_mapobjects_type')


############
# Features #
############

feature_parser = data_subparsers.add_parser(
    'feature', help='feature resources',
    description='Access feature resources.',
)
feature_subparsers = feature_parser.add_subparsers(
    dest='feature_methods', help='access methods'
)
feature_subparsers.required = True

feature_list_parser = feature_subparsers.add_parser(
    'ls', help='list features',
    description='List features for a given object type.',
    parents=[abstract_object_parser]
)
feature_list_parser.set_defaults(method='_list_features')

feature_rename_parser = feature_subparsers.add_parser(
    'rename', help='rename a feature',
    description='Rename a feature.',
    parents=[
        abstract_name_parser, abstract_object_parser,
        abstract_new_name_parser
    ]
)
feature_rename_parser.set_defaults(method='rename_feature')

feature_delete_parser = feature_subparsers.add_parser(
    'rm', help='delete a feature',
    description='Delete a feature.',
    parents=[abstract_name_parser, abstract_object_parser]
)
feature_delete_parser.set_defaults(method='delete_feature')


##################
# Feature values #
##################

feature_values_parser = data_subparsers.add_parser(
    'feature-values', help='feature values resources',
    description='Access feature values resources.',
)
feature_values_subparsers = feature_values_parser.add_subparsers(
    dest='feature_values_methods', help='access methods'
)
feature_values_subparsers.required = True

feature_value_download_parser = feature_values_subparsers.add_parser(
    'download', help='download feature values for segmented objects',
    description='''
        Download feature values for segmented objects as well as the
        corresponding metadata.
    ''',
    parents=[abstract_object_parser],
)
feature_value_download_parser.set_defaults(
    method='download_feature_values_and_metadata_files'
)


###########################
# Mapobject segmentations #
###########################

segmentation_parser = data_subparsers.add_parser(
    'segmentation', help='segmentation resources',
    description='Access segmentation resources.',
)
segmentation_subparsers = segmentation_parser.add_subparsers(
    dest='segmentation_methods', help='access methods'
)
segmentation_subparsers.required = True

segmentation_upload_parser = segmentation_subparsers.add_parser(
    'upload',
    help='upload segmenations from image file',
    description='''
        Upload object segmentations in from a 16-bit PNG image file.
        The image must be labeled such that background pixels have zero
        values and pixels within objects have unsigned integer values.

        WARNING: This approach only works when the image contains less
        than 65536 objects.
    ''',
    parents=[
        abstract_site_parser, abstract_tpoint_parser,
        abstract_zplane_parser, abstract_object_parser
    ]
)
segmentation_upload_parser.add_argument(
    '--filename', required=True, help='path to the file on disk'
)
segmentation_upload_parser.set_defaults(
    method='upload_segmentation_image_file'
)

segmentation_download_parser = segmentation_subparsers.add_parser(
    'download',
    help='download segmented objects as label image',
    description='''
        Download segmentations in form of a 16-bit PNG image file.

        WARNING: This approach only works when the image contains less
        than 65536 objects.
    ''',
    parents=[
        abstract_site_parser, abstract_tpoint_parser,
        abstract_zplane_parser, abstract_object_parser
    ]
)
segmentation_download_parser.add_argument(
    '--directory',
    help='''
        path to directory where file should be stored
        (defaults to temporary directory)
    '''
)
segmentation_download_parser.set_defaults(
    method='download_segmentation_image_file'
)

#######################
# Channel image files #
#######################

channel_image_parser = data_subparsers.add_parser(
    'channel-image', help='channel image resources',
    description='Access channel image resources.',
)
channel_image_subparsers = channel_image_parser.add_subparsers(
    dest='channel_image_methods', help='access methods'
)
channel_image_subparsers.required = True

channel_image_download_parser = channel_image_subparsers.add_parser(
    'download', help='download channel image',
    description='Download channel image to PNG file.',
    parents=[
        abstract_site_parser, abstract_tpoint_parser,
        abstract_zplane_parser, abstract_channel_parser
    ]
)
channel_image_download_parser.set_defaults(
    method='download_channel_image_file'
)
channel_image_download_parser.add_argument(
    '-i', '--cycle-index', dest='cycle_index', default=0,
    help='zero-based index of the cycle'
)
channel_image_download_parser.add_argument(
    '--correct', action='store_true',
    help='whether image should be corrected for illumination artifacts'
)
channel_image_download_parser.add_argument(
    '--directory',
    help='''
        path to directory where file should be stored
        (defaults to temporary directory)
    '''
)


