# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
class NotSupportedError(Exception):
    '''Error class that is raised when a feature is not supported by the program.
    '''


class MetadataError(Exception):
    '''Error class that is raised when a metadata element cannot be retrieved.
    '''


class SubmissionError(Exception):
    '''Error class that is raised when submitted jobs failed.
    '''


class JobDescriptionError(OSError):
    '''Error class that is raised when no job descriptor files are found.
    '''


class CliArgError(Exception):
    '''Error class that is raised when the value of an command line argument is
    invalid.
    '''


class RegexError(Exception):
    '''Error class that is raised when a regular expression pattern didn't match.
    '''


class StitchError(Exception):
    '''Error class that is raised when an error occurs upon stitching of
    images for the generation of a mosaic.
    '''


class PyramidCreationError(Exception):
    '''Error class that is raised when an error occurs upon creation of a pyramid
    image, i.e. stitching of images together to a large overview image.
    '''


class PipelineError(Exception):
    '''Base class for jterator pipeline errors.
    '''


class PipelineRunError(PipelineError):
    '''Error class that is raised when an error occurs upon running a jterator
    pipeline.
    '''


class PipelineDescriptionError(PipelineError):
    '''Error class that is raised when information in pipeline description is
    missing or incorrect.
    '''


class PipelineOSError(PipelineError):
    '''Error class that is raised when pipeline related files do not exist
    on disk.
    '''


class WorkflowError(Exception):
    '''Base class for workflow errors.
    '''


class DataError(Exception):
    '''Error class that is raised when data is not available.
    '''


class WorkflowDescriptionError(WorkflowError):
    '''Error class that is raised when the workflow is not correctly described.
    '''


class WorkflowTransitionError(WorkflowError):
    '''Error class that is raised when requirements for transition to the next
    workflow stage or step are not fulfilled.
    '''


class DataIntegrityError(Exception):
    '''Error class that is raised when a dataset doesn't fullfile certain
    requirements.
    '''


class RegistryError(Exception):
    '''Error class that is raised when a class is not registered.'''


class DataModelError(Exception):
    '''Error class that is raised when a model class has attributes that are
    not supported.
    '''
