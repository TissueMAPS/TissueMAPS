import os
import sys
import re
import logging
# import imp
import collections
import importlib
import traceback
import numpy as np
import rpy2.robjects
import rpy2.robjects.numpy2ri
from rpy2.robjects.packages import importr
from cStringIO import StringIO
from . import path_utils
from . import handles as hdls
from ..errors import PipelineRunError

logger = logging.getLogger(__name__)


class CaptureOutput(dict):
    '''
    Class for capturing standard output and error of function calls
    and redirecting the STDOUT and STDERR strings to a dictionary.

    Examples
    --------
    with CaptureOutput() as output:
        foo()
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


class ImageProcessingModule(object):
    '''
    Class for a Jterator module, the building block of a Jterator pipeline.
    '''

    def __init__(self, name, source_file, description):
        '''
        Initiate Module class.

        Parameters
        ----------
        name: str
            name of the module
        source_file: str
            path to program file that should be executed
        description: Dict[str, List[dict]]
            description of module input/output

        Returns
        -------
        tmlib.jterator.module.ImageProcessingModule
        '''
        self.name = name
        self.source_file = source_file
        self.handles = dict()
        self.handles['input'] = list()
        for item in description['input']:
            self.handles['input'].append(hdls.create_handle(**item))
        self.handles['output'] = list()
        for item in description['output']:
            self.handles['output'].append(hdls.create_handle(**item))
        self.outputs = dict()
        self.persistent_store = dict()

    def build_log_filenames(self, log_location, job_id):
        '''
        Build names of log-files into which the module will write
        standard output and error of the current job.

        Parameters
        ----------
        log_location: str
            path to directory for log output
        job_id: int
            one-based job index

        Returns
        -------
        Dict[str, str]
            absolute path to files for standard output and error
        '''
        out_file = os.path.join(log_location, '%s_%.5d.out' % (self.name, job_id))
        err_file = os.path.join(log_location, '%s_%.5d.err' % (self.name, job_id))
        return {'stdout': out_file, 'stderr': err_file}

    def build_figure_filename(self, figures_dir, job_id):
        '''
        Build name of figure file into which module will write figure output
        of the current job.

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
        figure_file = os.path.join(figures_dir, '%s_%.5d.html'
                                   % (self.name, job_id))
        return figure_file

    @property
    def keyword_arguments(self):
        '''
        Returns
        -------
        dict
            name and value of each input handle as key-value pairs
        '''
        kwargs = collections.OrderedDict()
        for handle in self.handles['input']:
            kwargs[handle.name] = handle.value
        return kwargs

    def build_error_message(self, stdout, stderr, message=''):
        '''
        Build a custom error massage that provides the standard input as well
        as standard output and error for an executed module.

        Parameters
        ----------
        kwargs: dict
            input arguments as key-value pairs
        stdout: str
            standard output of the module execution
        stderr: str
            standard error of the module execution

        Returns
        -------
        str
            error message
        '''
        message = '\n\n\nExecution of module "{0}" failed:\n'.format(self.name)
        message += '\n' + '---[ Module arguments ]---' \
            .ljust(80, '-') + '\n'
        for key, value in self.keyword_arguments.iteritems():
            message += '"{k}":\n{v}\n\n'.format(k=key, v=value)
        message += '\n' + '---[ Module standard output ]---' \
            .ljust(80, '-') + '\n' + stdout
        message += '\n' + '---[ Module standard error ]---' \
            .ljust(80, '-') + '\n' + stderr
        self.error_message = message
        return self.error_message

    def write_output_and_errors(self, stdout_file, stdout_data,
                                stderr_file, stderr_data):
        '''
        Write standard output and error to log file.

        Parameters
        ----------
        stdout_data: str
            standard output of the module execution
        stderr_data: str
            standard error of the module execution
        '''
        with open(stdout_file, 'w+') as output_log:
            output_log.write(stdout_data)
        with open(stderr_file, 'w+') as error_log:
            error_log.write(stderr_data)

    @property
    def language(self):
        '''
        Returns
        -------
        str
            language of the module (e.g. "python")
        '''
        return path_utils.determine_language(self.source_file)

    def _exec_m_module(self, engine):
        logger.debug('adding module to Matlab path: "%s"' % self.source_file)
        # engine.eval('addpath(\'{0}\');'.format(os.path.dirname(self.source_file)))
        module_name = os.path.splitext(os.path.basename(self.source_file))[0]
        engine.eval('import \'jtlib.modules.{0}\''.format(module_name))
        function_name = os.path.splitext(os.path.basename(self.source_file))[0]
        function_call_format_string = \
            '[{outputs}] = jtlib.modules.{name}({inputs})'
        kwargs = self.keyword_arguments
        logger.debug('evaluating Matlab function with INPUTS: "%s"',
                     '", "'.join(kwargs.keys()))
        output_names = [handle.name for handle in self.handles['output']]
        func_call_string = function_call_format_string.format(
                                    outputs=', '.join(output_names),
                                    name=function_name,
                                    inputs=', '.join(kwargs.keys()))
        # Add arguments as variable in Matlab session
        for name, value in kwargs.iteritems():
            engine.put(name, value)
        # Evaluate the function call
        # Unfortunately, the matlab_wrapper engine doesn't return
        # standard output and error (errors are caught, though).
        # "evalc" allows a dirty hack, but standard output is not returned
        # in case of an error :(
        engine.eval("stdout = evalc('{0};')".format(func_call_string))
        stdout = engine.get('stdout')
        stdout = re.sub(r'\n$', '', stdout)  # naicify string
        if stdout:
            print stdout

        for handle in self.handles['output']:
            val = engine.get('%s' % handle.name)
            if isinstance(val, np.ndarray):
                # Matlab returns arrays in Fortran order
                handle.value = val.copy(order='C')
            else:
                handle.value = val

        return self.handles['output']

    def _exec_py_module(self):
        logger.debug('importing module: "%s"' % self.source_file)
        module_name = os.path.splitext(os.path.basename(self.source_file))[0]
        module = importlib.import_module('jtlib.modules.%s' % module_name)
        func = getattr(module, module_name)
        kwargs = self.keyword_arguments
        logger.debug('evaluating Python function with INPUTS: "%s"',
                     '", "'.join(kwargs.keys()))
        py_out = func(**kwargs)
        if not isinstance(py_out, dict):
            raise PipelineRunError(
                    'Module "%s" must return an object of type dict.'
                    % self.name)

        for handle in self.handles['output']:
            if handle.name not in py_out.keys():
                raise PipelineRunError(
                        'Module "%s" didn\'t return output argument "%s".'
                        % (self.name, handle.name))
            handle.value = py_out[handle.name]

        return self.handles['output']

    def _exec_r_module(self):
        logger.debug('sourcing module: "%s"' % self.source_file)
        rpy2.robjects.r('source("{0}")'.format(self.source_file))
        rpy2.robjects.numpy2ri.activate()   # enables use of numpy arrays
        rpy2.robjects.pandas2ri.activate()  # enable use of pandas data frames
        function_name = os.path.splitext(os.path.basename(self.source_file))[0]
        func = rpy2.robjects.globalenv['{0}'.format(function_name)]
        kwargs = self.keyword_arguments
        logger.debug('evaluating R function with INPUTS: "%s"'
                     % '", "'.join(kwargs.keys()))
        # R doesn't have unsigned integer types
        for k, v in kwargs.iteritems():
            if isinstance(v, np.ndarray):
                if v.dtype == np.uint16 or v.dtype == np.uint8:
                    logging.debug(
                        'module "%s" input argument "%s": '
                        'convert unsigned integer data type to integer',
                        self.name, k)
                    kwargs[k] = v.astype(int)
            # TODO: we may have to translate pandas data frames into the
            # R equivalent
            # pd.com.convert_to_r_dataframe(v)
        args = rpy2.robjects.ListVector({k: v for k, v in kwargs.iteritems()})
        base = importr('base')
        r_out = base.do_call(func, args)

        for handle in self.handles['output']:
            # NOTE: R functions are supposed to return a list. Therefore
            # we can extract the output argument using rx2(name).
            # The R equivalent would be indexing the list with "[[name]]".
            if isinstance(r_out.rx2(handle.name), rpy2.robjects.vectors.DataFrame):
                # handle.value = pd.DataFrame(r_var.rx2(name))
                handle.value = rpy2.robjects.pandas2ri(r_out.rx2(handle.name))
            else:
                # handle.value = np.array(r_var.rx2(name))
                handle.value = rpy2.robjects.numpy2ri(r_out.rx2(handle.name))

        return self.handles['output']

    def _execute_module(self, engine):
        if self.language == 'Python':
            return self._exec_py_module()
        elif self.language == 'Matlab':
            return self._exec_m_module(engine)
        elif self.language == 'R':
            return self._exec_r_module()
        else:
            raise PipelineRunError('Language not supported.')

    def update_handles(self, store, plot):
        '''
        Update values of handles that define the arguments of the
        module function.

        Parameters
        ----------
        store: dict
            in-memory key-value store
        plot: bool
            whether plotting should be enabled

        Returns
        -------
        List[tmlib.jterator.handles.Handle]
            handles for input keyword arguments

        Note
        ----
        This method must be called BEFORE calling
        :py:method:`tmlib.jterator.module.Module.run`.
        '''
        for handle in self.handles['input']:
            if isinstance(handle, hdls.PipeHandle):
                try:
                    handle.value = store['pipe'][handle.key]
                except KeyError:
                    raise PipelineRunError(
                        'Value for argument "%s" was not created upstream '
                        'in the pipeline!' % self.name)
                except Exception:
                    raise
            elif isinstance(handle, hdls.Plot):
                # Overwrite to enforce headless mode if required.
                handle.value = plot
        return self.handles['input']

    def _get_reference_objects_name(self, handle):
        objects_names = [
            h.key for h in self.handles['input']
            if h.name == handle.objects_ref and
            isinstance(h, hdls.Objects)
        ]
        if len(objects_names) == 0:
            raise PipelineRunError(
                    'Invalid object reference for "%s" in module "%s"'
                    % (handle.name, self.name))
        return objects_names[0]

    def _get_reference_channel_name(self, handle):
        if handle.channel_ref is None:
            return None
        channel_names = [
            h.key for h in self.handles['input']
            if h.name == handle.channel_ref and
            isinstance(h, hdls.IntensityImage)
        ]
        if len(channel_names) == 0:
            raise PipelineRunError(
                    'Invalid channel reference for "%s" in module "%s"'
                    % (handle.name, self.name))
        return channel_names[0]

    def update_store(self, store):
        '''
        Update `store` with key-value pairs that were returned by the module
        function.

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
        :py:method:`tmlib.jterator.module.Module.run`.
        '''
        for i, handle in enumerate(self.handles['output']):
            if isinstance(handle, hdls.Figure):
                store['figures'].append(handle.value)
            elif isinstance(handle, hdls.Objects):
                store['objects'][handle.key] = handle
                store['pipe'][handle.key] = handle.value
            elif isinstance(handle, hdls.Features):
                object_name = self._get_reference_objects_name(handle)
                channel_name = self._get_reference_channel_name(handle)
                if channel_name is not None:
                    for name in handle.value.columns:
                        name += '_%s' % channel_name
                obj_handle = store['objects'][object_name]
                obj_handle.add_features(handle.value)
            elif isinstance(handle, hdls.Attribute):
                obj_names = [
                    h.key for h in self.handles['output'][i]
                    if h.name == handle.object_ref and
                    isinstance(h, hdls.Objects)
                ]
                if len(obj_names) == 0:
                    raise PipelineRunError(
                            'Invalid object reference for "%s" '
                            'in module "%s": %s'
                            % (handle.name, self.name))
                obj_handle = store['objects'][obj_names[0]]
                obj_handle.add_attribute(handle.value)
            else:
                store['pipe'][handle.key] = handle.value
        return store

    def run(self, engine=None):
        '''
        Execute a module, i.e. evaluate the corresponding function with
        the provided arguments.

        Parameters
        ----------
        input_handles: List[tmlib.jterator.handles.Handle]
            handles for arguments that are passed to the module function
        output_handles: List[tmlib.jterator.handles.Handle]
            handles for key-value pairs returned by the module function
        engine: matlab_wrapper.matlab_session.MatlabSession, optional
            engine for non-Python languages, such as Matlab (default: ``None``)

        Returns
        -------
        dict
            * "stdout": standard output
            * "stderr": standard error
            * "success": ``True`` when module completed successfully and
              ``False`` otherwise
            * "error_message": error message and traceback in case an
              Exception was raised while running the module

        Warning
        -------
        Call :py:method:`tmlib.jterator.module.Module.update_handles` before
        calling this method and
        :py:method:`tmlib.jterator.module.Module.update_store` afterwards.
        '''
        with CaptureOutput() as stream:
            # TODO: the StringIO approach prevents debugging of modules
            # build custom logger
            try:
                self._execute_module(engine)
                error = ''
                success = True
            except Exception as e:
                error = str(e)
                for tb in traceback.format_tb(sys.exc_info()[2]):
                    error += '\n' + tb
                success = False

        stdout = stream['stdout']
        stderr = stream['stderr']
        stderr += error
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)

        if not success:
            error_message = self.build_error_message(stdout, stderr)
        else:
            error_message = None

        return {
            'stdout': stdout,
            'stderr': stderr,
            'success': success,
            'error_message': error_message
        }

    def __str__(self):
        return ':%s: @ <%s>' % (self.name, self.source_file)
