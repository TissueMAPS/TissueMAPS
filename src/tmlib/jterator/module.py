import os
import sys
import re
import logging
# import imp
import importlib
import traceback
import collections
import numpy as np
import pandas as pd
import rpy2.robjects
import rpy2.robjects.numpy2ri
from rpy2.robjects.packages import importr
from cStringIO import StringIO
from . import path_utils
from ..errors import PipelineRunError
from ..errors import NotSupportedError

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
        description: dict
            description of module input/output

        Returns
        -------
        tmlib.jterator.module.ImageProcessingModule
        '''
        self.name = name
        self.source_file = source_file
        self.description = description
        self.pipeline_store = dict()
        self.persistent_store = dict()

    def build_log_filenames(self, log_dir, job_id):
        '''
        Build names of log-files into which the module will write
        standard output and error of the current job.

        Parameters
        ----------
        log_dir: str
            path to directory for log output
        job_id: int
            one-based job index

        Returns
        -------
        Dict[str, str]
            absolute path to files for standard output and error
        '''
        out_file = os.path.join(log_dir, '%s_%.5d.out' % (self.name, job_id))
        err_file = os.path.join(log_dir, '%s_%.5d.err' % (self.name, job_id))
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

    def build_error_message(self, input_data, stdout, stderr, message=''):
        '''
        Build a custom error massage that provides the standard input as well
        as standard output and error for an executed module.

        Parameters
        ----------
        input_data: dict
            the data parsed as input arguments to the module
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
        if input_data:
            message += '\n' + '---[ Module input arguments ]---' \
                .ljust(80, '-') + '\n'
            for key, value in input_data.iteritems():
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

    @staticmethod
    def save_figure(fig, figure_file):
        '''
        Write `plotly <https://plot.ly>`_ figure represented as
        HTML string with embedded javascript code to file.

        Parameters
        ----------
        fig: str
            figure as HTML string
        figure_file: str
            name of the figure file
        '''
        with open(figure_file, 'w') as f:
            f.write(fig)

    @property
    def language(self):
        '''
        Returns
        -------
        str
            language of the module (e.g. "python")
        '''
        return path_utils.determine_language(self.source_file)

    def _exec_m_module(self, inputs, output_names, engine):
        logger.debug('adding module to Matlab path: "%s"' % self.source_file)
        # engine.eval('addpath(\'{0}\');'.format(os.path.dirname(self.source_file)))
        module_name = os.path.splitext(os.path.basename(self.source_file))[0]
        engine.eval('import \'jtlib.modules.{0}\''.format(module_name))
        logger.debug('evaluating Matlab function with INPUTS: "%s"',
                     '", "'.join(inputs.keys()))
        for name, value in inputs.iteritems():
            engine.put('%s' % name, value)
        function_name = os.path.splitext(os.path.basename(self.source_file))[0]
        func_call = '[{args_out}, figure] = jtlib.modules.{name}({args_in})'.format(
                                    args_out=', '.join(output_names),
                                    name=function_name,
                                    args_in=', '.join(inputs.keys()))
        # Unfortunately, the matlab_wrapper engine doesn't return
        # standard output and error (errors are caught)
        engine.eval("stdout = evalc('{0};')".format(func_call))
        stdout = engine.get('stdout')
        stdout = re.sub(r'\n$', '', stdout)  # naicify string
        if stdout:
            print stdout
        for i, name in enumerate(output_names):
            m_var_np = engine.get('%s' % name).copy(order='C')
            logger.debug('dimensions of OUTPUT "{name}": {value}'.format(
                                            name=name,
                                            value=m_var_np.shape))
            logger.debug('type of OUTPUT "{name}": {value}'.format(
                                            name=name,
                                            value=type(m_var_np)))
            logger.debug('dtype of OUTPUT "{name}": {value}'.format(
                                            name=name,
                                            value=m_var_np.dtype))
            index = output_names.index(name)
            output_param = self.description['output'][index]
            if output_param['mode'] == 'pipe':
                self.pipeline_store[output_param['id']] = m_var_np
            else:
                raise NotSupportedError(
                        'Matlab module only supports mode "pipe"')

        try:
            self.figure = engine.get('figure')
        except:
            self.figure = ''

    def _exec_py_module(self, inputs, output_names):
        logger.debug('importing module: "%s"' % self.source_file)
        module_name = os.path.splitext(os.path.basename(self.source_file))[0]
        module = importlib.import_module('jtlib.modules.%s' % module_name)
        func = getattr(module, module_name)
        logger.debug('evaluating Python function with INPUTS: "%s"',
                     '", "'.join(inputs.keys()))
        py_out = func(**inputs)
        if not output_names:
            logger.debug('no output arguments specified in module description')
            return
        if not isinstance(py_out, dict):
            raise PipelineRunError(
                    'Module "%s" must return an object of type dict.'
                    % self.name)
        for i, name in enumerate(output_names):
            if name not in py_out.keys():
                raise PipelineRunError(
                        'Module "%s" didn\'t return output argument "%s".'
                        % (self.name, name))
            py_var_np = py_out[name]
            if not(isinstance(py_var_np, np.ndarray) or
                    isinstance(py_var_np, pd.DataFrame) or
                    isinstance(py_var_np, pd.Series)):
                raise PipelineRunError(
                        'Output of module "%s" must have type numpy.ndarray,'
                        'pandas.DataFrame, or pandas.Series' % self.name)
            logger.debug('dimensions of OUTPUT "{name}": {value}'.format(
                                            name=name,
                                            value=py_var_np.shape))
            logger.debug('type of OUTPUT "{name}": {value}'.format(
                                            name=name,
                                            value=type(py_var_np)))
            try:
                logger.debug('dtype of OUTPUT "{name}": {value}'.format(
                                            name=name,
                                            value=py_var_np.dtype))
            except:
                logger.debug('OUTPUT "{name} is a data frame'.format(
                                            name=name))

            index = output_names.index(name)
            output_param = self.description['output'][index]
            if output_param['mode'] == 'pipe':
                self.pipeline_store[output_param['id']] = py_var_np
            elif output_param['mode'] == 'store':
                self.persistent_store[output_param['ref']] = py_var_np
            else:
                raise NotSupportedError()

        self.figure = py_out.get('figure', '')

    def _exec_r_module(self, inputs, output_names):
        logger.debug('sourcing module: "%s"' % self.source_file)
        rpy2.robjects.r('source("{0}")'.format(self.source_file))
        rpy2.robjects.numpy2ri.activate()   # enables use of numpy arrays
        rpy2.robjects.pandas2ri.activate()  # enable use of pandas data frames
        function_name = os.path.splitext(os.path.basename(self.source_file))[0]
        func = rpy2.robjects.globalenv['{0}'.format(function_name)]
        logger.debug('evaluating R function with INPUTS: "%s"'
                     % '", "'.join(inputs.keys()))
        # R doesn't have unsigned integer types
        for k, v in inputs.iteritems():
            if isinstance(v, np.ndarray):
                if v.dtype == np.uint16 or v.dtype == np.uint8:
                    logging.debug(
                        'module "%s" input argument "%s": '
                        'convert unsigned integer data type to integer',
                        self.name, k)
                    inputs[k] = v.astype(int)
            # TODO: we may have to translate pandas data frames into the
            # R equivalent
            # pd.com.convert_to_r_dataframe(v)
        args = rpy2.robjects.ListVector({k: v for k, v in inputs.iteritems()})
        base = importr('base')
        r_out = base.do_call(func, args)
        for i, name in enumerate(output_names):
            # NOTE: R functions are supposed to return a list. Therefore
            # we can extract the output argument using rx2(name).
            # The R equivalent would be indexing the list with "[[name]]".
            if isinstance(r_out.rx2(name), rpy2.robjects.vectors.DataFrame):
                # r_var_np = pd.DataFrame(r_var.rx2(name))
                r_var_np = rpy2.robjects.pandas2ri(r_out.rx2(name))
            else:
                # r_var_np = np.array(r_var.rx2(name))
                r_var_np = rpy2.robjects.numpy2ri(r_out.rx2(name))
            logger.debug('dimensions of OUTPUT "{name}": {value}'.format(
                                            name=name,
                                            value=r_var_np.shape))
            logger.debug('type of OUTPUT "{name}": {value}'.format(
                                            name=name,
                                            value=type(r_var_np)))
            try:
                logger.debug('dtype of OUTPUT "{name}": {value}'.format(
                                            name=name,
                                            value=r_var_np.dtype))
            except:
                logger.debug('OUTPUT "{name} is a data frame'.format(
                                            name=name))

            index = output_names.index(name)
            output_param = self.description['output'][index]
            if output_param['mode'] == 'pipe':
                self.pipeline_store[output_param['id']] = r_var_np
            elif output_param['mode'] == 'store':
                self.persistent_store[output_param['ref']] = r_var_np
            else:
                raise NotSupportedError()

        try:
            self.figure = r_out.rx2('figure')
        except:
            self.figure = ''

    def _execute_module(self, inputs, output_names, engine=None):
        if self.language == 'Python':
            self._exec_py_module(inputs, output_names)
        elif self.language == 'Matlab':
            self._exec_m_module(inputs, output_names, engine)
        elif self.language == 'R':
            self._exec_r_module(inputs, output_names)
        else:
            raise PipelineRunError('Language not supported.')

    def prepare_inputs(self, images, upstream_output, plot):
        '''
        Prepare input data that will be parsed to the module.

        Parameters
        ----------
        images: Dict[str, numpy.ndarray]
            name of each image and the corresponding pixels array
        upstream_output: dict
            output data generated by modules upstream in the pipeline
        plot: bool
            whether plotting should be enabled

        Note
        ----
        Images are automatically aligned on the fly.

        Warning
        -------
        Be careful when activating plotting because plots are saved as *html*
        files on disk. Their generation requires memory and computation time
        and the files will accumulate on disk.

        Returns
        -------
        dict
            input arguments
        '''
        # Prepare input provided by handles
        inputs = collections.OrderedDict()
        input_names = list()
        for arg in self.description['input']:
            input_names.append(arg['name'])
            if arg['mode'] == 'constant':
                inputs[arg['name']] = arg['value']
            else:
                if arg['value'] in images.keys():
                    # Input pipeline data
                    inputs[arg['name']] = images[arg['value']]
                else:
                    # Upstream pipeline data
                    if arg['value'] is None:
                        continue  # empty value is tolerated for pipeline data
                    pipe_in = {
                        k: v for k, v in upstream_output.iteritems()
                        if k == arg['value']
                    }
                    if arg['value'] not in pipe_in:
                        # TODO: shouldn't this be handled by the checker?
                        raise PipelineRunError(
                                'Incorrect value "%s" for argument "%s" '
                                'in module "%s"'
                                % (arg['value'], arg['name'], self.name))
                    inputs[arg['name']] = pipe_in[arg['value']]
        inputs['plot'] = plot
        return inputs

    def run(self, inputs, engine=None):
        '''
        Execute a module, i.e. evaluate the corresponding function with
        the parsed input arguments as described by `handles`.

        Output has the following format::

            {
                'pipeline_store': ,     # dict
                'persistent_store': ,   # dict
                'stdout': ,             # str
                'stderr': ,             # str
                'success': ,            # bool
                'error_message': ,      # str
            }

        Parameters
        ----------
        inputs: dict
            input arguments of the module
        engine: matlab_wrapper.matlab_session.MatlabSession, optional
            engine for non-Python languages (default: ``None``)

        Returns
        -------
        dict
            output
        '''
        if self.description['output']:
            output_names = [
                o['name'] for o in self.description['output']
            ]
        else:
            output_names = []

        with CaptureOutput() as output:
            # TODO: the StringIO approach prevents debugging of modules
            # build custom logger
            try:
                self._execute_module(inputs, output_names, engine)
                success = True
                error = ''
            except Exception as e:
                error = str(e)
                for tb in traceback.format_tb(sys.exc_info()[2]):
                    error += '\n' + tb
                success = False

        stdout = output['stdout']
        sys.stdout.write(stdout)

        stderr = output['stderr']
        stderr += error
        sys.stderr.write(stderr)

        if success:
            output = {
                'pipeline_store': self.pipeline_store,
                'persistent_store': self.persistent_store,
                'figure': self.figure,
                'stdout': stdout,
                'stderr': stderr,
                'success': success,
                'error_message': None
            }
        else:
            output = {
                'pipeline_store': None,
                'persistent_store': None,
                'figure': None,
                'stdout': stdout,
                'stderr': stderr,
                'success': success,
                'error_message': self.build_error_message(
                                        inputs, stdout, stderr)
            }
        return output

    def __str__(self):
        return ':%s: @ <%s>' % (self.name, self.source_file)
