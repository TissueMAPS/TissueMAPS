#! /usr/bin/env python
"""
test_datasets.py [options] DATASET_DIR [PARAMS_FILE]

Upload each experiment in DATASET_DIR to a TM server, start the
ingestion workflow and wait until it's finished.  Results are
displayed to STDOUT and (optionally) written to a JUnit-format XML
file.

Optional argument PARAMS_FILE is the path to a YAML file specifying
experiment metadata (e.g., type of plates and workflow).  An example
of the required fields for an experiment is::

    Name_of_experiment_dir:
      # choices for microscope_type: cellvoyager, metamorph
      microscope_type: cellvoyager
      # choices for plate_acquisition_mode: basic, multiplexing
      plate_acquisition_mode: basic
      plate_format: 384
      # choices for workflow_type: canonical, multiplexing
      workflow_type: canonical

If PARAMS_FILE is omitted, a file named `TESTS.yml` in directory
DATASET_DIR is searched for.
"""

from __future__ import absolute_import, division, print_function


import cPickle as pickle
from datetime import datetime
import logging
from multiprocessing.dummy import Pool
import os
from os.path import basename, exists, isabs, isdir, join
import subprocess
import sys
from time import sleep, time

import click
import daiquiri
import json
import yaml
from yattag import Doc as XML, indent

from tmclient.api import TmClient


## aux functions

def abort(errmsg, exitcode=os.EX_SOFTWARE):
    """
    Abort execution, printing error message and returning the given
    exit code to the caller.
    """
    logging.error(errmsg)
    sys.exit(exitcode)


def is_empty_dir(path):
    """
    Return ``True`` if the directory at `path` is empty.
    """
    return len(os.listdir(path)) == 2


def listdir(path, exclude=None):
    """
    Like `os.listdir`, but omit any dotfiles and filter out any entry
    for which the optional ``exclude`` function returns ``True``.
    """
    for entry in os.listdir(path):
        if entry.startswith('.'):
            continue
        if exclude and exclude(entry):
            continue
        yield entry


def check_data_set_directory(path, params):
    """
    Return an error message string if the directory at `path` is *not*
    a dataset directory formatted according to the conventions
    expected by this script.

    If it is, then return ``None``.
    """
    if not exists(join(path, 'workflow_description.yaml')):
        return ("no `workflow_description.yaml` file.")
    plates_dir = join(path, 'plates')
    if not isdir(plates_dir):
        return ("no `plates` subdirectory inside.")
    if is_empty_dir(plates_dir):
        return ("`plates` subdirectory is empty.")
    for plate in listdir(plates_dir):
        acquisition_dir = join(plates_dir, plate, 'acquisitions')
        if not isdir(acquisition_dir):
            return ("acquisition subdirectory in plate `%s`" % plate)
        if is_empty_dir(acquisition_dir):
            return ("empty acquisition subdirectory in plate `%s`." % plate)
        if 'acquisitions' in params:
            for entry in params['acquisitions']:
                if not isdir(join(acquisition_dir, entry)):
                    return (
                        "missing acquisition directory `{entry}`"
                        .format(**locals()))
    jterator_dir = join(path, 'jterator')
    if not isdir(jterator_dir):
        return ("no `jterator` subdirectory.")
    return None


def compute_workflow_progress(wkf):
    """
    Return percentage of workflow completion.

    :param wkf: Response object gotten from `TmClient.get_workflow_status()`
    """
    tasks = wkf.get('subtasks', [])
    # the `depth=...` argument to `get_workflow_status()` sort of
    # truncates the output by returning ``None`` instead of tasks
    # deeper than requested -- be sure we really do have a dictionary
    # to recurse into
    if tasks and all(tasks):
        # all tasks are weighted equal (incorrect but easy)
        weight = 1.0 / len(tasks)
        return weight*sum(map(compute_workflow_progress, tasks), 0.0)
    else:
        return wkf.get('percent_done', 0.0)


def stem(filename):
    return os.path.splitext(basename(filename))[0]


class timing(object):
    def __init__(self, msg='', logger=logging):
        self.__msg = msg
        self.__log = logger
        self.start = 0
        self.stop = 0

    def begin(self):
        self.__log.info("Start: %s ...", self.__msg)
        self.start = time()
        self.stop = time()

    def end(self):
        if self.stop == self.start:
            self.stop = time()
        self.duration = self.stop - self.start
        self.__log.debug(
            "Done: %s (duration: %0.3fs).",
            self.__msg, self.duration)

    # context manager interface
    def __enter__(self):
        self.begin()
        return self
    def __exit__(self, exc_type, exc_value, tb):
        self.end()


## junit report generation

class Report(object):

    def __init__(self, title=''):
        self.title = title
        self.reset()

    def reset(self):
        """
        Reset report state to blank.

        This can be used to generate multiple JUnit XML files with a
        single `Report`:class: instance, resetting state after each
        write.
        """
        self._suites = []
        # counters
        self.ok = 0
        self.errored = 0
        self.failed = 0
        self.skipped = 0

    def error(self, suite, case, msg):
        self.errored += 1
        logging.error("Step `%s` errored: %s", case.name, msg)

    def fail(self, suite, case, msg):
        self.failed += 1
        logging.error("Step `%s` failed: %s", case.name, msg)

    def skip(self, suite, case, msg):
        self.skipped += 1
        logging.warning("Step `%s` skipped: %s", case.name, msg)

    def success(self, suite, case, msg):
        self.ok += 1
        logging.info("Step `%s` completed: %s", case.name, msg)

    def as_junit_xml(self,):
        xml, tag, text = XML().tagtext()
        xml.asis('<?xml version="1.0" encoding="UTF-8"?>')
        with tag('testsuites',
                 name=self.title,
                 tests=sum(len(suite._testcases) for suite in self._suites),
                 errors=self.errored,
                 failures=self.failed,
        ):
            for testsuite in self._suites:
                xml.asis(testsuite.as_junit_xml())
        return xml.getvalue()

    def print_terminal_output(self):
        click.echo("All done!")
        click.secho("    OK: {}".format(self.ok),
                    fg='green', bold=True)
        click.secho("  FAIL: {}".format(self.failed + self.errored),
                    fg='red', bold=True)
        click.secho("  SKIP: {}".format(self.skipped),
                    fg='yellow', bold=True)

    def new_test_suite(self, name, **properties):
        """
        Return a new `_Testsuite`:class: instance.

        The newly-created instance has this `Report`:class: object as
        parent and will automatically update it as `_Testcase`'s are
        marked with OK/error/etc.
        """
        suite = _Testsuite(name, id=len(self._suites),
                           parent=name, **properties)
        return self.add_test_suite(suite)

    def add_test_suite(self, suite):
        """
        Add a `_Testsuite`:class: instance to the report.
        """
        self._suites.append(suite)
        suite._parent = self
        self.ok += suite.ok
        self.errored += suite.errored
        self.failed += suite.failed
        self.skipped += suite.skipped
        return suite


class _Testsuite(timing):

    def __init__(self, name, **properties):
        self.name = name
        self.hostname = properties.pop('hostname', 'localhost')
        self._id = properties.pop('id', None)
        self._parent = properties.pop('parent', None)
        self._properties = properties
        self._testcases = []
        self.ok = 0
        self.errored = 0
        self.failed = 0
        self.skipped = 0
        super(_Testsuite, self).__init__(name)

    def error(self, case, msg):
        self.errored += 1
        if self._parent:
            self._parent.error(self, case, msg)

    def fail(self, case, msg):
        self.failed += 1
        if self._parent:
            self._parent.fail(self, case, msg)

    def skip(self, case, msg):
        self.skipped += 1
        if self._parent:
            self._parent.skip(self, case, msg)

    def success(self, case, msg):
        self.ok += 1
        if self._parent:
            self._parent.success(self, case, msg)

    def as_junit_xml(self):
        """
        Return Junit-format XML fragment.
        """
        xml, tag, text = XML().tagtext()
        with tag('testsuite',
                 name=self.name,
                 hostname=self.hostname,
                 time=(self.stop - self.start),
                 tests=len(self._testcases),
                 timestamp=datetime.fromtimestamp(self.start).isoformat(),
                 errors=self.errored,
                 failures=self.failed,
                 skipped=self.skipped,
        ):
            if self._id is not None:
                xml.attr(id=self._id)
            with tag('properties'):
                for key, value in self._properties.iteritems():
                    xml.stag('property', name=key, value=str(value))
            for testcase in self._testcases:
                if testcase.status is None:
                    with tag('error'):
                        text('Unknown outcome of this step.')
                else:
                    xml.asis(testcase.as_junit_xml())
        return xml.getvalue()

    def new_test_case(self, name, **properties):
        case = _Testcase(name, parent=self, **properties)
        return self.add_test_case(case)

    def add_test_case(self, case):
        # FIXME: should react on ok/error/whatever state
        self._testcases.append(case)
        return case


class _Testcase(timing):

    def __init__(self, name, **properties):
        super(_Testcase, self).__init__(name)
        self.name = name
        self.classname = properties.pop('classname', None)
        self.assertions = properties.pop('assertions', None)
        self.status = None
        self.stdout = None
        self.stderr = None
        self._parent = properties.get('parent', None)
        self._properties = properties

    def error(self, msg):
        self.end()
        self.status = 'error'
        self._msg = msg
        self._parent.error(self, msg)

    def fail(self, msg):
        self.end()
        self.status = 'failure'
        self._msg = msg
        self._parent.fail(self, msg)

    def skip(self, msg=''):
        self.end()
        self.status = 'skipped'
        self._msg = msg
        self._parent.skip(self, msg)

    def success(self, msg='OK'):
        self.end()
        self.status = 'success'
        self._msg = msg
        self._parent.success(self, msg)

    def as_junit_xml(self):
        xml, tag, text = XML().tagtext()
        with tag('testcase',
                 name=self.name,
                 time=(self.stop - self.start)):
            if self.classname is not None:
                xml.attr(classname=self.classname)
            if self.assertions is not None:
                xml.attr(assertions=self.assertions)
            with tag('properties'):
                for key, value in self._properties.iteritems():
                    xml.stag('property', name=key, value=str(value))
            if self.status == 'error':
                with tag('error', message=self._msg):
                    text(self._msg)
            elif self.status == 'failure':
                with tag('failure', message=self._msg):
                    text(self._msg)
            elif self.status == 'skipped':
                xml.stag('skipped', message=self._msg)
            if self.stdout is None:
                xml.stag('system-out')
            else:
                with tag('system-out'):
                    text(str(self.stdout))
            if self.stderr is None:
                xml.stag('system-err')
            else:
                with tag('system-err'):
                    text(str(self.stderr))
        return xml.getvalue()


## `tm_client` interface

class ApiTmClient(object):
    """
    Use the Python API for client-side operations.
    """

    def __init__(self, host, port, user, password, experiment_name):
        self._client = TmClient(host, port, user, password, experiment_name)

    class _Operation(object):

        def __init__(self, func, args, description=None):
            self.func = func
            self.args = args

            self.command = ''.join([
                self.func.__name__, '(',
                ', '.join(str(arg) for arg in args), ')'
            ])

            if description:
                self.description = description
            else:
                self.description = self.command

        def run(self):
            # see: https://stackoverflow.com/questions/12943819/how-to-prettyprint-a-json-file
            return json.dumps(
                self.func(* self.args),
                indent=4,
                sort_keys=True,
            )

    def _make_command(self, func, args, description=None):
        return self._Operation(func, args, description)


    ## actual client commands

    def create_experiment(self, workflow_type, microscope_type,
                          plate_format, plate_acquisition_mode):
        return self._make_command(
            self._client.create_experiment,
            (workflow_type, microscope_type,
             plate_format, plate_acquisition_mode),
        )

    def create_plate(self, plate_name):
        return self._make_command(
            self._client.create_plate, (plate_name,),
        )

    def create_acquisition(self, plate_name, acquisition_name):
        return self._make_command(
            self._client.create_acquisition,
            (plate_name, acquisition_name),
        )

    def upload_microscope_files(self, plate_name, acquisition_name, path):
        return self._make_command(
            self._client.upload_microscope_files,
            (plate_name, acquisition_name, path),
        )

    def upload_workflow_description_file(self, workflow_description_path):
        return self._make_command(
            self._client.upload_workflow_description_file,
            (workflow_description_path,),
        )

    def upload_jterator_project_files(self, jterator_project_path):
        return self._make_command(
            self._client.upload_jterator_project_files,
            (jterator_project_path,),
        )


class CommandLineTmClient(object):
    """
    Wrap invocation of ``tm_client`` commands.
    """

    def __init__(self, host, port, user, password, experiment_name):
        self.experiment_name = experiment_name
        # make tm_client invocation
        self._tm_client = [
            'tm_client', '-v',
            '--host', str(host), '--port', str(port),
            '--user', str(user), '--password', str(password)
        ]

    class _Operation(object):

        def __init__(self, tm_client, args, description=None):
            self._tm_client = tm_client
            self.args = args

            self._cmdline = tm_client + [str(arg) for arg in args]
            if description:
                self._description = description
            else:
                # omit auth data
                self._description = ' '.join(['tm_client', '...'] + list(args))

        @property
        def command(self):
            return ' '.join(self._cmdline)

        @property
        def description(self):
            return self._description

        def run(self):
            proc = subprocess.Popen(
                self._cmdline,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=None,  #open(os.devnull, 'r'),
                close_fds=True,
                shell=False
            )
            stdout, _ = proc.communicate()
            rc = proc.returncode
            if rc != 0:
                raise subprocess.CalledProcessError(
                    rc, (' '.join(self._cmdline)), stdout)
            else:
                return stdout

    def _make_command(self, *args, **kwargs):
        return self._Operation(
            self._tm_client, args,
            kwargs.pop('description', None))

    ## command implementations

    def create_experiment(self,
                          workflow_type, microscope_type,
                          plate_format, plate_acquisition_mode):
        return self._make_command(
            'experiment', 'create',
            '-n', self.experiment_name,
            '--workflow-type', workflow_type,
            '--microscope-type', microscope_type,
            '--plate-format', plate_format,
            '--plate-acquisition-mode', plate_acquisition_mode,
            description=("Create experiment `{}`"
                         .format(self.experiment_name))
        )

    def create_plate(self, plate_name):
        return self._make_command(
            'plate', '-e', self.experiment_name,
            'create', '-n', plate_name,
            description=("Create plate `{}`"
                         .format(plate_name))
        )

    def create_acquisition(self, plate_name, acquisition_name):
        return self._make_command(
            'acquisition', '-e', self.experiment_name,
            'create', '-p', plate_name, '-n', acquisition_name,
            description=("Create acquisition `{}`"
                         .format(acquisition_name))
        )

    def upload_microscope_files(self, plate_name, acquisition_name, path):
        return self._make_command(
            'microscope-file', '-e', self.experiment_name,
            'upload', '-p', plate_name, '-a', acquisition_name,
            path,
            description=("Upload image files")
        )

    def upload_workflow_description_file(self, workflow_description_path):
        return self._make_command(
            'workflow', '-e', self.experiment_name,
            'upload', '--file', workflow_description_path,
            description=("Upload workflow description")
        )

    def upload_jterator_project_files(self, jterator_project_path):
        return self._make_command(
            'jtproject', '-e', self.experiment_name,
            'upload', '--directory', jterator_project_path,
            description=("Upload Jterator project files")
        )


class Runner(object):
    """
    Run operations within test suites.
    """

    def __init__(self, suite, just_print=False, server_log=None):
        self.suite = suite
        self.just_print = just_print
        self.server_log = server_log

    def __call__(self, operation):
        if self.server_log:
            with open(self.server_log) as logfile:
                logfile.seek(0, os.SEEK_END)
                server_log_start = logfile.tell()
        with self.suite.new_test_case(operation.description) as testcase:
            testcase.classname = operation.command
            if self.just_print:
                testcase.skip("Dry run.")
            else:
                try:
                    stdout = operation.run()
                    testcase.success()
                    if stdout:
                        testcase.stdout = stdout
                except AssertionError as failure:
                    # treat this as a "non fatal" error: the
                    # workflow/testsuite can continue
                    testcase.fail(str(failure))
                except Exception as err:
                    # treat this as a fatal error: no more tests from
                    # the same suite will be run
                    testcase.error(str(err))
                    # exceptions raised by `subprocess` store the
                    # command's output in `.stdout`
                    try:
                        testcase.stdout = err.stdout
                    except AttributeError:
                        pass
                    raise self.Abort(
                        "Aborting test suite because of error: {}"
                        .format(err))
                finally:
                    # abuse test stderr to report server-side logs
                    if self.server_log:
                        with open(self.server_log) as logfile:
                            logfile.seek(0, os.SEEK_END)
                            server_log_end = logfile.tell()
                            logfile.seek(server_log_start, os.SEEK_SET)
                            testcase.stderr = logfile.read(server_log_end - server_log_start)

    class Abort(Exception):
        """
        Raised to signal that a test suite should be aborted.
        """
        pass


## more convenience functions

def collect_datasets(dataset_dir, test_params, only=None):
    datasets_to_test = []
    for entry in listdir(dataset_dir):
        if only and entry not in only:
            logging.info(
                "Ignoring dataset `%s`"
                " because of restrictions specified on command-line.",
                entry)
            continue
        path = join(dataset_dir, entry)
        if not isdir(path):
            logging.info(
                "Ignoring filesystem entry `%s`:"
                "is not a directory.", path)
            continue
        if entry not in test_params:
            logging.warning(
                "Ignoring directory `%s`:"
                " no tests parameters defined", path)
            continue
        err = check_data_set_directory(path, test_params[entry])
        if err:
            logging.warning(
                "Ignoring directory `%s`: %s", path, err)
            continue
        datasets_to_test.append(path)
    return datasets_to_test


def delete_experiment(host, port, user, password, experiment_name):
    """
    Return list of names of experiments that exist on the given TM server.
    """
    # NOTE: the experiment name is only given at initialization time...
    client = TmClient(host, port, user, password, experiment_name)
    return client.delete_experiment()


def get_experiment_data(dataset_path, test_params):
    name = basename(dataset_path)
    params = test_params[name]

    # provide default experiment name
    params.setdefault('name', name)

    # detect plates if not given
    plates_root_dir = join(dataset_path, 'plates')
    if 'plates' not in params:
        # discover plate names
        params['plates'] = [
            entry
            for entry in listdir(plates_root_dir)
            if isdir(join(plates_root_dir, entry))
        ]
        action = "Detected"
    else:
        action = "Configured"
    logging.debug(
        "%s plate names for dataset `%s`: %r",
        action, name, params['plates'])

    # detect acquisitions if not given
    if 'acquisitions' not in params:
        acquisitions_root_dir = join(
            plates_root_dir, plate, 'acquisitions')
        acquisitions = params['acquisitions'] = {}
        for plate in params['plates']:
            acquisitions[plate] = [
                entry
                for entry in listdir(acquisitions_root_dir)
                if isdir(join(acquisitions_root_dir, entry))
            ]
        action = "Detected"
    else:
        if isinstance(params['acquisitions'], list):
            acquisition_list = params['acquisitions']
        acquisitions = params['acquisitions'] = {}
        for plate in params['plates']:
            acquisitions[plate] = acquisition_list
        action = "Configured"
    logging.debug(
        "%s acquisitions for plate `%s` of dataset `%s`: %r",
        action, plate, name, params['acquisitions'])

    return name, params


def list_experiment_names(host, port, user, password):
    """
    Return list of names of experiments that exist on the given TM server.
    """
    # it's not possible to use the generic client as a client for a
    # specific experiment, as the experiment name is only given at
    # initialization time...
    client = TmClient(host, port, user, password)
    return [exp['name'] for exp in client.get_experiments()]


def load_test_params(dataset_dir, filename='TEST.yml'):
    # load test parameters
    if not isabs(filename):
        filename = join(dataset_dir, filename)
        if not exists(filename):
            abort(
                "No file `{0}` in directory `{1}`"
                " and no alternate TESTS_FILE specified"
                " on the command line."
                .format(basename(filename), dataset_dir))
    logging.debug("Loading test parameters file `%s` ...", filename)
    with open(filename) as stream:
        test_params = yaml.load(stream)
    logging.info("Loaded parameters for datasets: %r", test_params.keys())
    return test_params


def make_client(client_opt, host, port, user, password, experiment_name):
    if client_opt == 'api':
        return ApiTmClient(host, port, user, password, experiment_name)
    elif client_opt == 'cli':
        return CommandLineTmClient(host, port, user, password, experiment_name)
    else:
        raise RuntimeError(
            "Invalid choice for -c/--client: {}"
            .format(client_opt))


def run_workflow(case, host, port, user, password, experiment_name,
                 server_log=None, interval=30):
    # we really need an API client here, as the command-line
    # version does not print enough information to deduce the
    # workflow progress and termination status
    wkf_client = TmClient(host, port, user, password, experiment_name)
    if server_log:
        with open(server_log) as logfile:
            logfile.seek(0, os.SEEK_END)
            server_log_start = logfile.tell()
    try:
        wkf_client.submit_workflow()
        response = wkf_client.get_workflow_status(depth=1)
        while not response['done']:
            sleep(interval)
            # as of 2018-04-27, TM generates a 6 levels deep (!!)
            # hierarchy of tasks for the ingestion workflow -- be sure
            # we capture all of it (for better reporting and for
            # debugging purposes).
            response = wkf_client.get_workflow_status(depth=8)
            logging.debug(
                "client.get_workflow_status(%s) => %r",
                experiment_name, response)
            percent_done = compute_workflow_progress(response)
            logging.info(
                "%s: Workflow %.2f%% done.",
                experiment_name, percent_done)
        if response['failed']:
            case.fail('Workflow failed (%.2f%% done)' % percent_done)
        else:
            case.success("Workflow successfully completed!")
    except Exception as err:
        case.error(str(err))
    finally:
        # abuse test stderr to report server-side logs
        if server_log:
            with open(server_log) as logfile:
                logfile.seek(0, os.SEEK_END)
                server_log_end = logfile.tell()
                logfile.seek(server_log_start, os.SEEK_SET)
                case.stderr = logfile.read(server_log_end - server_log_start)


def setup_logging(verbose=0):
    global logging
    progname = basename(sys.argv[0])
    daiquiri.setup(
        level=(logging.ERROR - 10*verbose),
        program_name=progname)
    logging = daiquiri.getLogger(progname)


def write_junit_xml(report, tests_file, dataset_dir, dataset_name=None):
    # use a different file name depending on whether this is a
    # single dataset report or not (``dataset_name=None``)
    junit_filename_parts = [
        stem(tests_file),
        basename(dataset_dir),
        # can't use `.isoformat()` here because otherwise the `:`
        # separating the time part make the first part of the file
        # name look like an (invalid) protocol specifier in
        # relative links
        datetime.now().strftime('%Y-%m-%d-%H.%M.%S')
    ]
    if dataset_name:
        junit_filename_parts.insert(2, dataset_name)

    # `junit2html` has a bug: it will lowercase target file names in
    # links, but still create those files with the case they're given,
    # resulting in broken links.  Try to prevent it by ensuring our
    # JUnit XML files have lowercase names...
    junit_file = (
        '-'.join(junit_filename_parts) + '.xml'
    ).lower()
    logging.debug("Writing XML test report to file: `%s`", junit_file)

    with open(junit_file, 'w') as output:
        output.write(indent(report.as_junit_xml()))


## main

@click.command()
@click.argument('dataset_dir',
                type=click.Path(exists=True, file_okay=False))
@click.argument('tests_file',
                default=None,
                required=False,
                type=click.Path(exists=True, dir_okay=False))
@click.argument('only', nargs=-1)
@click.option('--host', '-H', envvar='TM_HOST', default='localhost',
              help="Name or IP address of server running TissueMAPS.")
@click.option('--port', '-P', envvar='TM_PORT', type=int, default=80,
              help="TCP port where the TissueMAPS server is listening.")
@click.option('--user', '-u', envvar='TM_USER', default=os.environ.get('USER'))
@click.password_option('--password', '-p', envvar='TM_PASSWORD')
@click.option('-c', '--client', 'client_opt',
              type=click.Choice(['api', 'cli']), default='api',
              help=("Whether to use the `tm_client` command (`cli`)"
                    " or the `TmClient` Python object API (`api`)."
                    " to perform requests to the server."))
@click.option('-i', '--polling-interval', '--interval',
              type=int, default=30,
              help=("How often to poll for status updates"
                    " when running workflows."))
@click.option('-j', '--jobs', '--concurrent',
              type=int, default=1,
              help=("Test this many datasets in parallel."
                    " Use '-j0' to run on as many threads"
                    " as there are CPUs on the computer."))
@click.option('-l', '--server-log', default=None,
              help="Path to server log to include in case of failed operations.")
@click.option('-v', '--verbose', count=True,
              help="Increase output verbosity.")
@click.option('--force/--no-force', default=False,
              help=("Forcefully remove existing experiments"
                    " with the same name as test cases"
                    " before running tests."))
@click.option('--aggregate/--no-aggregate', default=False,
              help=("Write a single JUnit XML report"
                    " containing results for all datasets."))
@click.option('-n', '--no-act', '--just-print',
              is_flag=True, default=False,
              help=("Only print what would be executed,"
                    " but do not perform any actual"
                    " operation on the server."))
def main(dataset_dir, tests_file, only,
         host, port, user, password,
         client_opt='api', server_log=None, interval=30, force=False,
         concurrent=1, aggregate=False, verbose=0, just_print=False):

    setup_logging(verbose)

    if just_print:
        logging.warning(
            "This is a simulation,"
            " no command will actually be performed!")

    # remove trailing `/` if present, otherwise
    # `basename(dataset_dir)` returns the empty string
    if dataset_dir.endswith('/'):
        dataset_dir = dataset_dir[:-1]

    # collect datasets to be tested
    test_params = load_test_params(dataset_dir, tests_file)
    datasets_to_test = collect_datasets(dataset_dir, test_params, only)
    if not datasets_to_test:
        abort("No datasets to test!")
    logging.info("Will test datasets: %r", datasets_to_test)

    existing_experiments = list_experiment_names(host, port, user, password)

    # actual code to run the tests
    def do_test_dataset(dataset_path):
        name, params = get_experiment_data(dataset_path, test_params)
        experiment_name = params.pop('name')
        params['client'] = client_opt
        client = make_client(client_opt, host, port, user, password, experiment_name)

        # check if an experiment with this name already exists
        if experiment_name in existing_experiments:
            if force:
                with timing(
                        "deleting old experiment `{}` ..."
                        .format(experiment_name)):
                    if not just_print:
                        delete_experiment(host, port, user, password, experiment_name)
            else:
                logging.error(
                    "Experiment `%s` already exists."
                    " Remove it before re-running this test.",
                    experiment_name)
                return

        # start actual testing
        with _Testsuite(name, **params) as suite:
            run = Runner(suite, just_print, server_log)

            try:
                # create experiment
                run(client.create_experiment(
                    params['workflow_type'], params['microscope_type'],
                    params['plate_format'], params['plate_acquisition_mode']))

                for plate in params['plates']:
                    # create plate(s)
                    run(client.create_plate(plate))

                    # create and upload acquisition(s)
                    for acquisition in params['acquisitions'][plate]:
                        acquisition_dir = join(
                            dataset_path,
                            'plates', plate,
                            'acquisitions', acquisition)
                        run(client.create_acquisition(plate, acquisition))
                        run(client.upload_microscope_files(plate, acquisition, acquisition_dir))

                workflow_description_path = join(dataset_path, params.get('workflow_description_path', 'workflow_description.yaml'))
                run(client.upload_workflow_description_file(workflow_description_path))

                jterator_project_path = join(dataset_path, params.get('jterator_project_path', 'jterator'))
                run(client.upload_jterator_project_files(jterator_project_path))

                with suite.new_test_case("Running workflow") as case:
                    if not just_print:
                        run_workflow(
                            case, host, port, user, password,
                            experiment_name, server_log, interval)

            except Runner.Abort as err:
                logging.warning("%s", err)

            return suite

    # do (possibly) parallel processing
    report = Report(basename(dataset_dir))
    proc = Pool(processes=(concurrent or None))
    suites = proc.imap_unordered(do_test_dataset, datasets_to_test)
    errors = False
    for suite in suites:
        if not suite:
            # `do_test_dataset` errored out
            continue
        report.add_test_suite(suite)
        if not aggregate:
            if not just_print:
                write_junit_xml(report, tests_file, dataset_dir, suite.name)
            report.print_terminal_output()
            if report.errored > 0 or report.failed > 0:
                errors = True
            report.reset()
    if aggregate:
        if not just_print:
            write_junit_xml(report, tests_file, dataset_dir)
        report.print_terminal_output()
        if report.errored > 0 or report.failed > 0:
            errors = True
        report.reset()

    if errors:
        return 2
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())
