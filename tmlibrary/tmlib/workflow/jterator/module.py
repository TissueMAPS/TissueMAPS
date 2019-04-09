# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2019 University of Zurich.
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
import sys
import re
import logging
import imp
import collections
import importlib
import traceback
import numpy as np
from cStringIO import StringIO


from tmlib.workflow.jterator.utils import determine_language
from tmlib.workflow.jterator import handles as hdls
from tmlib.errors import PipelineRunError

logger = logging.getLogger(__name__)


class CaptureOutput(dict):
    '''Class for capturing standard output and error and storing the strings
    in dictionary.

    Examples
    --------
    with CaptureOutput() as output:
        foo()

    Warning
    -------
    Using this approach screws up debugger break points.
    '''
    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = self._stringio_out = StringIO()
        sys.stderr = self._stringio_err = StringIO()
        return self

    def __exit__(self, *args):
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        output = self._stringio_out.getvalue()
        error = self._stringio_err.getvalue()
        self.update({'stdout': output, 'stderr': error})


class ImageAnalysisModule(object):

    '''Class for a Jterator module, the building block of an image analysis
    pipeline.
    '''

    def __init__(self, name, source_file, handles):
        '''
        Parameters
        ----------
        name: str
            name of the module
        source_file: str
            name or path to program file that should be executed
        handles: tmlib.workflow.jterator.description.HandleDescriptions
            description of module input/output as provided
        '''
        self.name = name
        self.source_file = source_file
        self.handles = handles
        self.outputs = dict()
        self.persistent_store = dict()

    def build_figure_filename(self, figures_dir, job_id):
        '''Builds name of figure file into which module will write figure
        output of the current job.

        Parameters
        ----------
        figures_dir: str
            path to directory for figure output
        job_id: int
            one-based job index

        Returns
        -------
        str
            absolute path to the figure file
        '''
        return os.path.join(figures_dir, '%s_%.5d.json' % (self.name, job_id))

    @property
    def keyword_arguments(self):
        '''dict: name and value of each input handle as key-value pairs'''
        kwargs = collections.OrderedDict()
        for handle in self.handles.input:
            kwargs[handle.name] = handle.value
        return kwargs

    @property
    def language(self):
        '''str: language of the module (e.g. "Python")'''
        return determine_language(self.source_file)

    def _exec_m_module(self, engine):
        module_name = os.path.splitext(os.path.basename(self.source_file))[0]
        logger.debug(
            'import module "%s" from source file: %s',
            module_name, self.source_file
        )
        # FIXME: this inserts the wrong directory if the MATLAB module
        # has the form `+directory` or `@directory` -- let's allow
        # this for the moment since the module discovery code only
        # deals with single-file modules, but it needs to be revisited
        source_dir = os.path.dirname(self.source_file)
        logger.debug(
            'adding module source directory `%s` to MATLAB path ...',
            source_dir
        )
        engine.eval(
            "addpath('{0}');".format(source_dir)
        )
        engine.eval('version = {0}.VERSION'.format(module_name))
        function_call_format_string = '[{outputs}] = {name}.main({inputs});'
        # NOTE: Matlab doesn't add imported classes to the workspace. It access
        # the "VERSION" property, we need to assign it to a variable first.
        version = engine.get('version')
        if version != self.handles.version:
            raise PipelineRunError(
                'Version of source and handles is not the same.'
            )
        kwargs = self.keyword_arguments
        logger.debug(
            'evaluate main() function with INPUTS: "%s"',
            '", "'.join(kwargs.keys())
        )
        output_names = [handle.name for handle in self.handles.output]
        func_call_string = function_call_format_string.format(
            outputs=', '.join(output_names),
            name=module_name,
            inputs=', '.join(kwargs.keys())
        )
        # Add arguments as variable in Matlab session
        for name, value in kwargs.iteritems():
            engine.put(name, value)
        # Evaluate the function call
        # NOTE: Unfortunately, the matlab_wrapper engine doesn't return
        # standard output and error (exceptions are caught, though).
        # TODO: log to file
        engine.eval(func_call_string)

        for handle in self.handles.output:
            val = engine.get('%s' % handle.name)
            if isinstance(val, np.ndarray):
                # Matlab returns arrays in Fortran order
                handle.value = val.copy(order='C')
            else:
                handle.value = val

        return self.handles.output

    def _exec_py_module(self):
        module_name = os.path.splitext(os.path.basename(self.source_file))[0]
        logger.debug(
            'import module "%s" from source file: %s',
            module_name, self.source_file
        )
        module = imp.load_source(module_name, self.source_file)
        if module.VERSION != self.handles.version:
            raise PipelineRunError(
                "Module source file `%s` has version %s"
                " but handles are version %s."
                % (self.source_file, module.VERSION, self.handles.version)
            )
        func = getattr(module, 'main', None)
        if func is None:
            raise PipelineRunError(
                'Module source file "%s" must contain a "main" function.'
                % module_name
            )
        kwargs = self.keyword_arguments
        logger.debug(
            'evaluate main() function with INPUTS: "%s"',
            '", "'.join(kwargs.keys())
        )
        py_out = func(**kwargs)
        # TODO: We could import the output class and check for its type.
        if not isinstance(py_out, tuple):
            raise PipelineRunError(
                'Module "%s" must return an object of type tuple.' % self.name
            )

        # Modules return a namedtuple.
        for handle in self.handles.output:
            if not hasattr(py_out, handle.name):
                raise PipelineRunError(
                    'Module "%s" didn\'t return output argument "%s".'
                    % (self.name, handle.name)
                )
            handle.value = getattr(py_out, handle.name)

        return self.handles.output

    def _exec_r_module(self):
        try:
            import rpy2.robjects
            from rpy2.robjects import numpy2ri
            from rpy2.robjects import pandas2ri
            from rpy2.robjects.packages import importr
        except ImportError:
            raise ImportError(
                'R module cannot be run, because '
                '"rpy2" package is not installed.'
            )
        module_name = os.path.splitext(os.path.basename(self.source_file))[0]
        logger.debug(
            'import module "%s" from source file: %s', self.source_file
        )
        logger.debug('source module: "%s"', self.source_file)
        rpy2.robjects.r('source("{0}")'.format(self.source_file))
        module = rpy2.robjects.r[module_name]
        version = module.get('VERSION')[0]
        if version != self.handles.version:
            raise PipelineRunError(
                'Version of source and handles is not the same.'
            )
        func = module.get('main')
        numpy2ri.activate()   # enables use of numpy arrays
        pandas2ri.activate()  # enable use of pandas data frames
        kwargs = self.keyword_arguments
        logger.debug(
            'evaluate main() function with INPUTS: "%s"',
            '", "'.join(kwargs.keys())
        )
        # R doesn't have unsigned integer types
        for k, v in kwargs.iteritems():
            if isinstance(v, np.ndarray):
                if v.dtype == np.uint16 or v.dtype == np.uint8:
                    logging.debug(
                        'module "%s" input argument "%s": '
                        'convert unsigned integer data type to integer',
                        self.name, k
                    )
                    kwargs[k] = v.astype(int)
            elif isinstance(v, pd.DataFrame):
                # TODO: We may have to translate pandas data frames explicitly
                # into the R equivalent.
                # pandas2ri.py2ri(v)
                kwargs[k] = v
        args = rpy2.robjects.ListVector({k: v for k, v in kwargs.iteritems()})
        base = importr('base')
        r_out = base.do_call(func, args)

        for handle in self.handles.output:
            # NOTE: R functions are supposed to return a list. Therefore
            # we can extract the output argument using rx2().
            # The R equivalent would be indexing the list with "[[]]".
            if isinstance(r_out.rx2(handle.name), rpy2.robjects.vectors.DataFrame):
                handle.value = pandas2ri.ri2py(r_out.rx2(handle.name))
                # handle.value = pd.DataFrame(r_out.rx2(handle.name))
            else:
                # NOTE: R doesn't have an unsigned integer data type.
                # So we cast to uint16.
                handle.value = numpy2ri.ri2py(r_out.rx2(handle.name)).astype(
                    np.uint16
                )
                # handle.value = np.array(r_out.rx2(handle.name), np.uint16)

        return self.handles.output

    def update_handles(self, store, headless=True):
        '''Updates values of handles that define the arguments of the
        module function.

        Parameters
        ----------
        store: dict
            in-memory key-value store
        headless: bool, optional
            whether plotting should be disabled (default: ``True``)

        Returns
        -------
        List[tmlib.jterator.handles.Handle]
            handles for input keyword arguments

        Note
        ----
        This method must be called BEFORE calling
        ::meth:`tmlib.jterator.module.Module.run`.
        '''
        logger.debug('update handles')
        for handle in self.handles.input:
            if isinstance(handle, hdls.PipeHandle):
                try:
                    handle.value = store['pipe'][handle.key]
                except KeyError:
                    raise PipelineRunError(
                        'Value for argument "%s" was not created upstream '
                        'in the pipeline: %s' % (self.name, handle.key)
                    )
                except Exception:
                    raise
            elif isinstance(handle, hdls.Plot) and headless:
                # Overwrite to enforce headless mode if required.
                handle.value = False
        return self.handles.input

    def _get_objects_name(self, handle):
        '''Determines the name of the segmented objects that are referenced by
        a `Features` handle.

        Parameters
        ----------
        handle: tmlib.workflow.jterator.handle.Features
            output handle with a `objects` attribute, which provides a
            reference to an input handle

        Returns
        -------
        str
            name of the referenced segmented objects
        '''
        objects_names = [
            h.key for h in self.handles.input + self.handles.output
            if h.name == handle.objects and
            isinstance(h, hdls.SegmentedObjects)
        ]
        if len(objects_names) == 0:
            raise PipelineRunError(
                'Invalid object for "%s" in module "%s": %s'
                % (handle.name, self.name, handle.objects)
            )
        return objects_names[0]

    def _get_reference_objects_name(self, handle):
        '''Determines the name of the segmented objects that are referenced by
        a `Features` handle.

        Parameters
        ----------
        handle: tmlib.workflow.jterator.handle.Features
            output handle with a `objects_ref` attribute, which provides a
            reference to an input handle

        Returns
        -------
        str
            name of the referenced segmented objects
        '''
        objects_names = [
            h.key for h in self.handles.input
            if h.name == handle.objects_ref and
            isinstance(h, hdls.SegmentedObjects)
        ]
        if len(objects_names) == 0:
            raise PipelineRunError(
                'Invalid object reference for "%s" in module "%s": %s'
                % (handle.name, self.name, handle.objects)
            )
        return objects_names[0]

    def _get_reference_channel_name(self, handle):
        '''Determines the name of the channel that is referenced by a
        `Features` handle.

        Parameters
        ----------
        handle: tmlib.workflow.jterator.handle.Features
            output handle with a `channel_ref` attribute, which provides a
            reference to an input handle

        Returns
        -------
        str
            name of the referenced channel
        '''
        if handle.channel_ref is None:
            return None
        channel_names = [
            h.key for h in self.handles.input
            if h.name == handle.channel_ref and
            isinstance(h, hdls.IntensityImage)
        ]
        if len(channel_names) == 0:
            raise PipelineRunError(
                'Invalid channel reference for "%s" in module "%s": %s'
                % (handle.name, self.name, handle.channel_ref)
            )
        return channel_names[0]

    def update_store(self, store):
        '''Updates `store` with key-value pairs that were returned by the
        module function.

        Parameters
        ----------
        store: dict
            in-memory key-value store

        Returns
        -------
        store: dict
            updated in-memory key-value store

        Note
        ----
        This method must be called AFTER calling
        ::meth:`tmlib.jterator.module.Module.run`.
        '''
        logger.debug('update store')
        for i, handle in enumerate(self.handles.output):
            if isinstance(handle, hdls.Figure):
                logger.debug('add value of Figure handle to store')
                store['current_figure'] = handle.value
            elif isinstance(handle, hdls.SegmentedObjects):
                logger.debug('add value of SegmentedObjects handle to store')
                # Measurements need to be reset.
                handle.measurements = []
                store['objects'][handle.key] = handle
                store['pipe'][handle.key] = handle.value
            elif isinstance(handle, hdls.Measurement):
                logger.debug('add value of Measurement handle to store')
                ref_objects_name = self._get_reference_objects_name(handle)
                objects_name = self._get_objects_name(handle)
                ref_channel_name = self._get_reference_channel_name(handle)
                new_names = list()
                for name in handle.value[0].columns:
                    if ref_objects_name != objects_name:
                        new_name = '%s_%s' % (ref_objects_name, name)
                    else:
                        new_name = str(name)  # copy
                    if ref_channel_name is not None:
                        new_name += '_%s' % ref_channel_name
                    new_names.append(new_name)
                for t in range(len(handle.value)):
                    handle.value[t].columns = new_names
                store['objects'][objects_name].add_measurement(handle)
            else:
                store['pipe'][handle.key] = handle.value
        return store

    def run(self, engine=None):
        '''Executes a module, i.e. evaluate the corresponding function with
        the keyword arguments provided by
        :class:`tmlib.workflow.jterator.handles`.

        Parameters
        ----------
        engine: matlab_wrapper.matlab_session.MatlabSession, optional
            engine for non-Python languages, such as Matlab (default: ``None``)

        Note
        ----
        Call ::meth:`tmlib.jterator.module.Module.update_handles` before
        calling this method and
        ::meth:`tmlib.jterator.module.Module.update_store` afterwards.
        '''
        if self.language == 'Python':
            return self._exec_py_module()
        elif self.language == 'Matlab':
            return self._exec_m_module(engine)
        elif self.language == 'R':
            return self._exec_r_module()
        else:
            raise PipelineRunError('Language not supported.')

    def __str__(self):
        return (
            '<%s(name=%r, source=%r)>'
            % (self.__class__.__name__, self.name, self.source_file)
        )
