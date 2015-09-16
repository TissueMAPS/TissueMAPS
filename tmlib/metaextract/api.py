import os
import re
import shutil
from glob import glob
from natsort import natsorted
from cached_property import cached_property
from ..formats import Formats
from ..cluster import ClusterRoutines


class MetadataExtractor(ClusterRoutines):

    '''
    Class for extraction of metadata from microscopic image files using the
    Bio-Formats command line tool
    `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_.

    Upon extraction, the metadata is formatted according to the
    `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_
    and written to XML files.
    '''

    def __init__(self, experiment, prog_name, logging_level='critical'):
        '''
        Initialize an instance of class MetadataExtractor.

        Parameters
        ----------
        experiment: Experiment
            experiment object that holds information about the content of the
            experiment directory
        prog_name: str
            name of the corresponding command line interface
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)

        See also
        --------
        `tmlib.cfg`_
        '''
        super(MetadataExtractor, self).__init__(prog_name, logging_level)
        self.experiment = experiment
        self.prog_name = prog_name

    @property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where joblist file and log output will be stored
        '''
        self._project_dir = os.path.join(self.experiment.dir,
                                         'tmaps_%s' % self.prog_name)
        return self._project_dir

    @cached_property
    def cycles(self):
        '''
        Returns
        -------
        List[Wellplate or Slide]
            cycle objects
        '''
        self._cycles = self.experiment.cycles
        return self._cycles

    @staticmethod
    def _get_ome_xml_filename(image_filename):
        return re.sub(r'(%s)$' % os.path.splitext(image_filename)[1],
                      '.ome.xml', image_filename)

    def create_joblist(self, **kwargs):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        cfg_file: str
            absolute path to custom configuration file
        **kwargs: dict
            empty - no additional arguments
        '''
        joblist = dict()
        joblist['run'] = list()
        output_files = list()
        count = 0
        for i, cycle in enumerate(self.cycles):
            image_filenames = [f for f in os.listdir(cycle.image_upload_dir)
                               if os.path.splitext(f)[1]
                               in Formats().supported_extensions]
            input_files = [os.path.join(cycle.image_upload_dir, f)
                           for f in image_filenames]
            if not input_files:
                raise IOError('No image files of supported formats '
                              'found in upload directory.')
            output_files.extend([os.path.join(cycle.ome_xml_dir,
                                              self._get_ome_xml_filename(f))
                                 for f in image_filenames])

            for j in xrange(len(input_files)):
                count += 1
                joblist['run'].append({
                    'id': count,
                    'inputs': [input_files[j]],
                    'outputs': list(),
                    'cycle': cycle.name
                })

        joblist['collect'] = {
            'inputs': list(),
            'outputs': output_files
        }
        return joblist

    def _build_run_command(self, batch):
        input_filename = batch['inputs'][0]
        command = [
            'showinf', '-omexml-only', '-nopix', '-novalid', '-no-upgrade',
            input_filename
        ]
        return command

    def run_job(self, batch):
        # Java job
        raise AttributeError('"%s" step has no "run" routine'
                             % self.prog_name)

    def _build_collect_command(self):
        command = [self.prog_name]
        command.append(self.experiment.dir)
        command.extend(['collect'])
        return command

    def collect_job_output(self, batch, **kwargs):
        '''
        The *showinf* command prints the OME-XML string to standard output.
        GC3Pie redirects the standard output to a log file. Here we copy the
        content of the log file to the files specified by the `ome_xml_files`
        attribute.

        The extracted metadata is used to create custom metadata, which will be
        subsequently used by TissueMAPS.

        Parameters
        ----------
        batch: dict
            description of the *collect* job
        **kwargs: dict
            additional variable input arguments as key-value pairs
        '''
        for i, f in enumerate(batch['outputs']):
            output_files = glob(os.path.join(
                                self.log_dir, '*_job-%.5d*.out' % (i+1)))
            # Take the most recent one, in case there are outputs of previous
            # submissions
            output_files = natsorted(output_files)
            shutil.copyfile(output_files[0], f)

    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
