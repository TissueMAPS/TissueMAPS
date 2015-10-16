import os
import imp
import sys
import re
import logging
import traceback
import collections
import numpy as np
import rpy2.robjects as robjects
import rpy2.robjects.numpy2ri
from rpy2.robjects.packages import importr
from cStringIO import StringIO
from . import path_utils
from ..errors import PipelineRunError

logger = logging.getLogger(__name__)


class CaptureOutput(dict):
    '''
    Class for capturing standard output and error of function calls.

    Usage::

        with CaptureOutput() as output:
            my_function(arg)

    This redirects the STDOUT and STDERR string and stores it in a dictionary. 
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

    def __init__(self, name, module_file, handles_description, experiment_dir):
        '''
        Initiate Module class.

        Parameters
        ----------
        name: str
            name of the module
        module_file: str
            path to program file that should be executed
        handles_description: dict
            description of module input/output
        experiment_dir: str
            path to experiment directory
        '''
        self.name = name
        self.module_file = module_file
        self.handles_description = handles_description
        self.experiment_dir = experiment_dir
        self.outputs = dict()

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
        figure_file = os.path.join(figures_dir, '%s_%.5d.figure'
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

    @property
    def language(self):
        '''
        Returns
        -------
        str
            language of the module
        '''
        self._language = path_utils.determine_language(self.module_file)
        return self._language

    def _exec_m_module(self, inputs, output_names, engine):
        logger.debug('adding module to Matlab path: "%s"' % self.module_file)
        engine.eval('addpath(\'{0}\');'.format(os.path.dirname(self.module_file)))
        logger.debug('evaluating Matlab function with INPUTS: "%s"'
              % '", "'.join(inputs.keys()))
        for name, value in inputs.iteritems():
            engine.put('%s' % name, value)
        func_call = '[{output_args}] = {function_name}({inputs_args});'.format(
                                    output_args=', '.join(output_names),
                                    function_name=self.name,
                                    inputs_args=', '.join(inputs.keys()))
        # Capture standard output and error
        engine.eval("out = evalc('{0}')".format(func_call))
        out = engine.get('out')
        out = re.sub(r'\n$', '', out)  # naicify string
        print out  # print to standard output
        for i, name in enumerate(output_names):
            m_out = engine.get('%s' % name)
            logger.debug('value of OUTPUT "{name}":\n{value}'.format(
                                            name=name, value=m_out))
            logger.debug('dimensions of OUTPUT "{name}": {value}'.format(
                                            name=name, value=m_out.shape))
            logger.debug('type of OUTPUT "{name}": {value}'.format(
                                            name=name, value=type(m_out)))
            logger.debug('dtype of elements of OUTPUT "{name}": {value}'.format(
                                            name=name, value=m_out.dtype))
            output_value = [
                o['value'] for o in self.handles_description['output']
                if o['name'] == name
            ][0]
            self.outputs[output_value] = m_out

    def _exec_py_module(self, inputs, output_names):
        logger.debug('importing module: "%s"' % self.module_file)
        imp.load_source(self.name, self.module_file)
        func = getattr(__import__(self.name, fromlist=[self.name]), self.name)
        logger.debug('evaluating Python function with INPUTS: "%s"'
              % '", "'.join(inputs.keys()))
        py_out = func(**inputs)
        if not output_names:
            return
        if not len(py_out) == len(output_names):
            raise PipelineRunError('number of outputs is incorrect.')
        for i, name in enumerate(output_names):
            # NOTE: The Python function is supposed to return a namedtuple!
            if py_out._fields[i] != name:
                raise PipelineRunError('Incorrect output names.')
            logger.debug('value of OUTPUT "{name}":\n{value}'.format(
                                            name=name, value=py_out[i]))
            logger.debug('dimensions of OUTPUT "{name}": {value}'.format(
                                            name=name, value=py_out[i].shape))
            logger.debug('type of OUTPUT "{name}": {value}'.format(
                                            name=name, value=type(py_out[i])))
            logger.debug('dtype of elements of OUTPUT "{name}": {value}'.format(
                                            name=name, value=py_out[i].dtype))
            output_value = [
                o['value'] for o in self.handles_description['output']
                if o['name'] == name
            ][0]
            self.outputs[output_value] = py_out[i]
        if 'Figure' in py_out._fields:
            self.figure = py_out.Figure

    def _exec_r_module(self, inputs, output_names):
        logger.debug('sourcing module: "%s"' % self.module_file)
        robjects.r('source("{0}")'.format(self.module_file))
        robjects.numpy2ri.activate()  # enables use of numpy arrays
        func = robjects.globalenv['{0}'.format(self.name)]
        logger.debug('evaluating R function with INPUTS: "%s"'
                     % '", "'.join(inputs.keys()))
        args = robjects.ListVector({k: v for k, v in inputs.iteritems()})
        base = importr('base')
        r_var = base.do_call(func, args)
        for i, name in enumerate(output_names):
            r_var_np = np.array(r_var.rx2(name))
            logger.debug('value of OUTPUT "{name}":\n{value}'.format(
                                            name=name, value=r_var_np))
            logger.debug('dimensions of OUTPUT "{name}": {value}'.format(
                                            name=name, value=r_var_np.shape))
            logger.debug('type of OUTPUT "{name}": {value}'.format(
                                            name=name, value=type(r_var_np)))
            logger.debug('dtype of elements of OUTPUT "{name}": {value}'.format(
                                            name=name, value=r_var_np.dtype))
            output_value = [
                o['value'] for o in self.handles_description['output']
                if o['name'] == name
            ][0]
            self.outputs[output_value] = r_var_np

    def _execute_module(self, inputs, output_names, engine=None):
        if self.language == 'Python':
            self._exec_py_module(inputs, output_names)
        elif self.language == 'Matlab':
            self._exec_m_module(inputs, output_names, engine)
        elif self.language == 'R':
            self._exec_r_module(inputs, output_names)
        else:
            raise PipelineRunError('Language not supported.')

    def prepare_inputs(self, layers, upstream_output, data_file, figure_file,
                       job_id):
        '''
        Prepare input data that will be parsed to the module.

        Parameters
        ----------
        layers: Dict[str, dict]
            name of each layer and the corresponding image object
        upstream_output: dict
            output data generated by modules upstream in the pipeline
        data_file: str
            absolute path to the data file
        figure_file: str
            absolute path to the figure file
        job_id: str
            one-based job identifier number

        Returns
        -------
        dict
            keys: name of the input argument, values: input data

        Note
        ----
        The image is automatically aligned on the fly.
        '''
        # Prepare input provided by handles
        inputs = collections.OrderedDict()
        input_names = list()
        for i in self.handles_description['input']:
            input_names.append(i['name'])
            if i['class'] == 'parameter':
                inputs[i['name']] = i['value']
            else:
                if i['value'] in layers.keys():
                    # Input pipeline data
                    inputs[i['name']] = layers[i['value']]
                else:
                    # Upstream pipeline data
                    if i['value'] is None:
                        continue  # empty value is ok for pipeline data
                    pipe_in = {k: v for k, v in upstream_output.iteritems()
                               if k == i['value']}
                    inputs[i['name']] = pipe_in[i['value']]
        # Add additional stuff => kwargs
        inputs['data_file'] = data_file
        inputs['figure_file'] = figure_file
        inputs['experiment_dir'] = self.experiment_dir
        inputs['plot'] = self.handles_description['plot']
        inputs['job_id'] = job_id
        return inputs

    def run(self, inputs, engine=None):
        '''
        Execute a module, i.e. evaluate the corresponding function with
        the parsed input arguments as described by the *handles*.

        Output has the format::

            {
                'data': dict,
                'stdout': str,
                'stderr': str,
                'success': bool,
                'error_message': str
            }

        Returns
        -------
        dict
            output
        '''
        if self.handles_description['output']:
            output_names = [
                o['name'] for o in self.handles_description['output']
            ]
        else:
            output_names = []

        with CaptureOutput() as output:
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
                'data': self.outputs,
                'stdout': stdout,
                'stderr': stderr,
                'success': True,
                'error_message': None
            }
        else:
            output = {
                'data': None,
                'stdout': stdout,
                'stderr': stderr,
                'success': False,
                'error_message': self.build_error_message(inputs,
                                                          stdout, stderr)
            }
        return output

    def __str__(self):
        return ':%s: @ <%s>' % (self.name, self.module_file)
