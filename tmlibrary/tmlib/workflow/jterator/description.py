# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
import os
import re
import logging

from tmlib.errors import PipelineDescriptionError
from tmlib.workflow.jterator import handles

logger = logging.getLogger(__name__)


class PipelineDescription(object):

    '''Description of a *jterator* pipeline.'''

    __slots__ = ('_input', '_output', '_pipeline')

    def __init__(self, input, pipeline, output):
        '''
        Parameters
        ----------
        input: Dict[str, List[Dict[str, str]]]
            description of pipeline input
        pipeline: List[Dict[str, str]]
            description of pipeline
        output: Dict[str, List[Dict[str, str]]]
            description of pipeline output
        '''
        self.input = self._create_input_description(input)
        self.output = self._create_output_description(output)
        self.pipeline = self._create_pipeline_descriptions(pipeline)

    def _create_input_description(self, value):
        if not isinstance(value, dict):
            raise PipelineDescriptionError(
                'Value of "input" in pipeline description file must be a '
                'mapping.'
            )
        try:
            return PipelineInputDescription(**value)
        except TypeError as err:
            raise PipelineDescriptionError(
                'Incorrect arguments provided for "input" section of pipeline '
                'description:\n%s' % str(err)
            )

    def _create_output_description(self, value):
        if not isinstance(value, dict):
            raise PipelineDescriptionError(
                'Value of "output" in pipeline description file must be a '
                'mapping.'
            )
        try:
            return PipelineOutputDescription(**value)
        except TypeError as err:
            raise PipelineDescriptionError(
                'Incorrect arguments provided for "output" section of pipeline '
                'description:\n%s' % str(err)
            )

    def _create_pipeline_descriptions(self, value):
        if not isinstance(value, list):
            raise PipelineDescriptionError(
                'Value of "pipeline" in pipeline description file must be an '
                'array.'
            )
        description = list()
        for i, v in enumerate(value):
            if not isinstance(v, dict):
                raise PipelineDescriptionError(
                    'Value of item #%d in "pipeline" section of pipeline '
                    'description must be a mapping.'
                )
            # NOTE: The "name" attribute is only required for the viewer.
            if 'name' in v:
                module_name = v.pop('name')
            try:
                module = PipelineModuleDescription(**v)
            except TypeError as err:
                raise PipelineDescriptionError(
                    'Incorrect arguments provided for item #%d in "pipeline" '
                    'section of pipeline description:\n%s' % (i, str(err))
                )
            description.append(module)
        return description

    @property
    def input(self):
        '''tmlib.workflow.jterator.description.PipelineInputDescription:
        input that should be available to modules in the pipeline
        '''
        return self._input

    @input.setter
    def input(self, value):
        if not isinstance(value, PipelineInputDescription):
            raise TypeError(
                'Attribute "input" must have type PipelineInputDescription.'
            )
        self._input = value

    @property
    def output(self):
        '''tmlib.workflow.jterator.description.PipelineOutputDescription:
        output of a pipeline that should be persisted
        '''
        return self._output

    @output.setter
    def output(self, value):
        if not isinstance(value, PipelineOutputDescription):
            raise TypeError(
                'Attribute "output" must have type PipelineOutputDescription.'
            )
        self._output = value

    @property
    def pipeline(self):
        '''List[tmlib.workflow.jterator.description.PipelineModuleDescription]:
        modules that should be run
        '''
        return self._pipeline

    @pipeline.setter
    def pipeline(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "pipeline" must have type list.')
        for v in value:
            if not isinstance(v, PipelineModuleDescription):
                raise TypeError(
                    'Items of attribute "pipeline" must have type '
                    'PipelineModuleDescription.'
                )
        self._pipeline = value

    def to_dict(self):
        '''Returns attributes "input", "pipeline" and "output" as key-value
        pairs.

        Returns
        -------
        dict
        '''
        attrs = dict()
        attrs['input'] = self.input.to_dict()
        attrs['output'] = self.output.to_dict()
        attrs['pipeline'] = [m.to_dict() for m in self.pipeline]
        return attrs


class PipelineInputDescription(object):

    '''Input of a *jterator* pipeline.'''

    __slots__ = ('_channels', '_objects')

    def __init__(self, channels=None, objects=None):
        '''
        Parameters
        ----------
        channels: List[dict], optional
            description of channels input
        objects: List[dict], optional
            description of objects input
        '''
        if channels is None:
            channels = []
        if objects is None:
            objects = []
        self.channels = self._create_channel_descriptions(channels)
        self.objects = self._create_object_descriptions(objects)

    def _create_channel_descriptions(self, value):
        if not isinstance(value, list):
            raise PipelineDescriptionError(
                'Value of "channels" in "input" section of pipeline descripion '
                'must be an array.'
            )
        descriptions = list()
        for i, v in enumerate(value):
            if not isinstance(v, dict):
                raise PipelineDescriptionError(
                    'Value of item #%d of "channels" in "input" section of '
                    'pipeline description must be a mapping.' % i
                )
            ch = PipelineChannelInputDescription(**v)
            descriptions.append(ch)
        return descriptions

    def _create_object_descriptions(self, value):
        if not isinstance(value, list):
            raise PipelineDescriptionError(
                'Value of "objects" in "input" section of pipeline descripion '
                'must be an array.'
            )
        descriptions = list()
        for i, v in enumerate(value):
            if not isinstance(v, dict):
                raise PipelineDescriptionError(
                    'Value of item #%d of "objects" in "input" section of '
                    'pipeline description must be a mapping.' % i
                )
            obj = PipelineObjectInputDescription(**v)
            descriptions.append(obj)
        return descriptions

    @property
    def channels(self):
        '''List[tmlib.workflow.jterator.description.PipelineChannelInputDescription]:
        pipeline channels input
        '''
        return self._channels

    @channels.setter
    def channels(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "channels" must have type list.')
        for v in value:
            if not isinstance(v, PipelineChannelInputDescription):
                raise TypeError(
                    'Items of attribute "channels" must have type '
                    'PipelineChannelInputDescription.'
                )
        self._channels = value

    @property
    def objects(self):
        '''List[tmlib.workflow.jterator.description.PipelineObjectInputDescription]:
        pipeline objects input
        '''
        return self._objects

    @objects.setter
    def objects(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "objects" must have type list.')
        for v in value:
            if not isinstance(v, PipelineObjectInputDescription):
                raise TypeError(
                    'Items of attribute "objects" must have type '
                    'PipelineObjectInputDescription.'
                )
        self._objects = value

    def to_dict(self):
        '''Returns attributes objects", and "channels" as key-value pairs.

        Returns
        -------
        dict
        '''
        attrs = dict()
        attrs['objects'] = [o.to_dict() for o in self.objects]
        attrs['channels'] = [c.to_dict() for c in self.channels]
        return attrs


class PipelineOutputDescription(object):

    '''Description of the output of a *jterator* pipeline.'''

    __slots__ = ('_objects', )

    def __init__(self, objects):
        '''
        Parameters
        ----------
        objects: List[dict]
            description of objects input
        '''
        self.objects = self._create_object_descriptions(objects)

    def _create_object_descriptions(self, value):
        if not isinstance(value, list):
            raise PipelineDescriptionError(
                'Value of "objects" in "input" section of pipeline descripion '
                'must be an array.'
            )
        descriptions = list()
        for i, v in enumerate(value):
            if not isinstance(v, dict):
                raise PipelineDescriptionError(
                    'Value of item #%d of "objects" in "input" section of '
                    'pipeline description must be a mapping.' % i
                )
            obj = PipelineObjectOutputDescription(**v)
            descriptions.append(obj)
        return descriptions

    @property
    def objects(self):
        '''List[tmlib.workflow.jterator.description.PipelineObjectOutputDescription]:
        pipeline objects input
        '''
        return self._objects

    @objects.setter
    def objects(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "objects" must have type list.')
        for v in value:
            if not isinstance(v, PipelineObjectOutputDescription):
                raise TypeError(
                    'Items of attribute "objects" must have type '
                    'PipelineObjectOutputDescription.'
                )
        self._objects = value

    def to_dict(self):
        '''Returns attributes "name" and "objects" as key-value pairs.

        Returns
        -------
        dict
        '''
        attrs = dict()
        attrs['objects'] = [o.to_dict() for o in self.objects]
        return attrs


class PipelineChannelInputDescription(object):

    '''A :class:`Channel <tmlib.models.channel.Channel>` that should be made
    available to the pipeline.
    '''

    __slots__ = ('_name', '_correct')

    def __init__(self, name, correct=True):
        '''
        Parameters
        ----------
        name: str
            name of the channel
        correct: bool, optional
            whether images should be corrected (default: ``True``)
        '''
        self.name = name
        self.correct = correct

    @property
    def name(self):
        '''str: name of the channel'''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "name" must have type basestring.')
        self._name = str(value)

    @property
    def correct(self):
        '''bool: whether images should be corrected for illumination artifacts
        '''
        return self._correct

    @correct.setter
    def correct(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "correct" must have type bool.')
        self._correct = value

    def to_dict(self):
        '''Returns attributes "name" and "correct" as key-value pairs.

        Returns
        -------
        dict
        '''
        return {'name': self.name, 'correct': self.correct}


class PipelineObjectInputDescription(object):

    '''A :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>` that
    should be made available to the pipeline.
    '''

    __slots__ = ('name', )

    def __init__(self, name):
        '''
        Parameters
        ----------
        name: str
            name of the object type
        '''
        self.name = name

    @property
    def name(self):
        '''str: name of the objects type'''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "name" must have type basestring.')
        self._name = str(name)

    def to_dict(self):
        '''Returns attribute "name" as key-value pair.

        Returns
        -------
        dict
        '''
        return {'name': self.name}


class PipelineObjectOutputDescription(object):

    '''Registered
    :class:`SegmentedObjects <tmlib.workflow.jterator.handles.SegmentedObjects>`
    that should be persisted as
    :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`.
    '''

    __slots__ = ('_name', '_as_polygons')

    def __init__(self, name, as_polygons=True):
        '''
        Parameters
        ----------
        name: str
            name of the object type
        as_polygons: bool, optional
            whether objects should be represented as polygons
            (if ``False`` only centroid coordinates will be stored;
            default: ``True``)
        '''
        self.name = name
        self.as_polygons = as_polygons

    @property
    def name(self):
        '''str: name of the objects type'''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "name" must have type basestring.')
        self._name = str(value)

    @property
    def as_polygons(self):
        '''bool: whether object should be represented as polygons'''
        return self._as_polygons

    @as_polygons.setter
    def as_polygons(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "as_polygons" must have type bool.')
        self._as_polygons = value

    def to_dict(self):
        '''Returns attributes "name" and "as_polygons" as key-value pairs.

        Returns
        -------
        dict
        '''
        return {'name': self.name, 'as_polygons': self.as_polygons}


class PipelineModuleDescription(object):

    __slots__ = ('_handles', '_source', '_active')

    def __init__(self, handles, source, active=True):
        '''
        Parameters
        ----------
        handles: str
            path to the *.handles.yaml* file
        source: str
            name of the module source code file in the :mod:`jtmodules` package
        active: bool, optional
            whether the module should be run (default: ``True``)
        '''
        self.handles = handles
        self.source = source
        self.active = active

    @property
    def name(self):
        return os.path.splitext(
            os.path.splitext(os.path.basename(self.handles))[0]
        )[0]

    @property
    def handles(self):
        '''str: path to handles file'''
        return self._handles

    @handles.setter
    def handles(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "handles" must have type basestring.')
        self._handles = str(value)

    @property
    def source(self):
        '''str: name of the source'''
        return self._source

    @source.setter
    def source(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "source" must have type basestring.')
        self._source = str(value)

    @property
    def active(self):
        '''bool: whether module should be run'''
        return self._active

    @active.setter
    def active(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "active" must have type bool.')
        self._active = value

    def to_dict(self):
        '''Returns attributes "handles", "source" and "active" as key-value
        pairs.

        Returns
        -------
        dict
        '''
        return {
            'handles': self.handles,
            'source': self.source,
            'active': self.active
        }


class HandleDescriptions(object):

    '''Description of a *jterator* module's parameters and return value.'''

    __slots__ = ('_version', '_input', '_output')

    def __init__(self, version, input, output):
        '''
        Parameters
        ----------
        version: str
            module version
        input: List[dict]
            description of module input parameters
        output: List[dict]
            description of module return value
        '''
        self.version = version
        self.input = self._create_input_descriptions(input)
        self.output = self._create_output_descriptions(output)

    @property
    def version(self):
        '''str: version of the module

        Note
        ----
        Must follow semantic versioning and match ``VERSION`` defined in the
        corresponding module source file.
        '''
        return self._version

    @version.setter
    def version(self, value):
        if not isinstance(value, basestring):
            raise PipelineDescriptionError(
                'Value of "version" in handles description must be a string.'
            )
        if not re.search(r'^\d+\.\d+\.\d+$', value):
            raise PipelineDescriptionError(
                'Value of "version" in handles description '
                'must follow semantic versioning.'
            )
        self._version = str(value)

    def _create_input_descriptions(self, value):
        if not isinstance(value, list):
            raise PipelineDescriptionError(
                'Value of "input" in handles description must be an array.'
            )
        names = list()
        descriptions = list()
        for i, v in enumerate(value):
            if not isinstance(v, dict):
                raise PipelineDescriptionError(
                    'Input item #%d in handles description must be a mapping.'
                    % i
                )
            if 'type' not in v:
                raise PipelineDescriptionError(
                    'Input item #%d in handles description requires key "type".'
                    % i
                )
            handle_type = v.pop('type')
            try:
                Handle = getattr(handles, handle_type)
            except AttributeError:
                raise PipelineDescriptionError(
                    'Type "%s" of input item #%d in handles description '
                    'is not valid.' % (handle_type, i)
                )
            try:
                h = Handle(**v)
            except TypeError as err:
                raise PipelineDescriptionError(
                    'Arguments for type "%s" of input item #%d '
                    'in handles description are incorrect:\n%s' %
                    (handle_type, i, str(err))
                )
            if not(isinstance(h, handles.InputHandle) or
                    isinstance(h, handles.PipeHandle)):
                raise PipelineDescriptionError(
                    'Type "%s" is not a valid input handle.' % handle_type
                )
            descriptions.append(h)
            names.append(v['name'])
        if len(set(names)) < len(value):
            raise PipelineDescriptionError(
                'Names of input items in handles description must be unique.'
            )
        return descriptions

    def _create_output_descriptions(self, value):
        if not isinstance(value, list):
            raise PipelineDescriptionError(
                'Value of "output" in handles description must be an array.'
            )
        names = list()
        descriptions = list()
        for i, v in enumerate(value):
            if not isinstance(v, dict):
                raise PipelineDescriptionError(
                    'Output item #%d in handles description must be a mapping.'
                    % i
                )
            if 'type' not in v:
                raise PipelineDescriptionError(
                    'Output item #%d in handles description requires key "type".'
                    % i
                )
            handle_type = v.pop('type')
            try:
                Handle = getattr(handles, handle_type)
            except AttributeError:
                raise PipelineDescriptionError(
                    'Type "%s" of output item #%d in handles description '
                    'is not valid.' % (handle_type, i)
                )
            try:
                h = Handle(**v)
            except TypeError as err:
                raise PipelineDescriptionError(
                    'Arguments for type "%s" of output item #%d '
                    'in handles description are incorrect:\n%s' %
                    (handle_type, i, str(err))
                )
            if not(isinstance(h, handles.OutputHandle) or
                    isinstance(h, handles.PipeHandle)):
                raise PipelineDescriptionError(
                    'Type "%s" is not a valid output handle.' % handle_type
                )
            descriptions.append(h)
            names.append(v['name'])
        if len(set(names)) < len(value):
            raise PipelineDescriptionError(
                'Names of output items in handles description must be unique.'
            )
        return descriptions

    @property
    def input(self):
        '''List[Union[tmlib.workflow.jterator.handles.InputHandle,
        tmlib.workflow.jterator.handles.PipeHandle]]: input handles
        '''
        return self._input

    @input.setter
    def input(self, value):
        if not isinstance(value, list):
            raise TypeError('Argument "input" must have type list.')
        for v in value:
            if not(isinstance(v, handles.InputHandle) or
                    isinstance(v, handles.PipeHandle)):
                raise TypeError(
                    'Items of argument "input" must have type InputHandle or '
                    'PipeHandle.'
                )
        self._input = value

    @property
    def output(self):
        '''List[Union[tmlib.workflow.jterator.handles.OutputHandle,
        tmlib.workflow.jterator.handles.PipeHandle]]: output handles
        '''
        return self._output

    @output.setter
    def output(self, value):
        if not isinstance(value, list):
            raise TypeError('Argument "output" must have type list.')
        for v in value:
            if not(isinstance(v, handles.OutputHandle) or
                    isinstance(v, handles.PipeHandle)):
                raise TypeError(
                    'Items of argument "output" must have type OutputHandle or '
                    'PipeHandle.'
                )
        self._output = value

    def to_dict(self):
        '''Returns attributes "version", "input" and "output" as key-value pairs.

        Returns
        -------
        dict
        '''
        return {
            'version': self.version,
            'input': [i.to_dict() for i in self.input],
            'output': [o.to_dict() for o in self.output]
        }
