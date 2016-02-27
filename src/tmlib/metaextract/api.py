import os
import re
from ..api import ClusterRoutines


class MetadataExtractor(ClusterRoutines):

    '''
    Class for extraction of metadata from microscopic image files.

    Extracted metadata is formatted according to the
    `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_
    and written to XML files.
    '''

    def __init__(self, experiment, prog_name, verbosity, **kwargs):
        '''
        Initialize an instance of class MetadataExtractor.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level
        kwargs: dict
            mapping of additional key-value pairs that are ignored
        '''
        super(MetadataExtractor, self).__init__(
                experiment, prog_name, verbosity)

    @staticmethod
    def _get_ome_xml_filename(image_filename):
        return re.sub(r'(%s)$' % os.path.splitext(image_filename)[1],
                      '.ome.xml', image_filename)

    def create_job_descriptions(self, args):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.metaextract.args.MetaextractArgs
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        job_descriptions = dict()
        job_descriptions['run'] = list()
        count = 0
        for source in self.experiment.sources:
            for acquisition in source.acquisitions:

                batches = self._create_batches(acquisition.image_files,
                                               args.batch_size)

                for j, files in enumerate(batches):
                    count += 1
                    job_descriptions['run'].append({
                        'id': count,
                        'inputs': {
                            'image_files': [
                                os.path.join(acquisition.image_dir, f)
                                for f in files
                            ]
                        },
                        'outputs': {
                            'omexml_files': [
                                os.path.join(acquisition.omexml_dir,
                                             self._get_ome_xml_filename(f))
                                for f in files
                            ]
                        }
                    })

        return job_descriptions

    def _build_run_command(self, batch):
        # TODO: This approach could become problematic when the batch_size is
        # too big because the number of characters that can be parsed via
        # the command line is limited.
        input_filenames = ','.join(batch['inputs']['image_files'])
        output_filenames = ','.join(batch['outputs']['omexml_files'])
        command = [
            'extract_omexml',
            '-i', input_filenames, '-o', output_filenames
        ]
        return command

    def run_job(self, batch):
        '''
        Not implemented.

        The class doesn't implement a :py:meth:`run_job` method because the
        actual processing is done in Java. Specifically, we use the
       `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_
        Bioformats command line tool to extract metadata from image files
        in `OMEXML` format.
        '''
        raise NotImplementedError(
                '"%s" object has no "run_job" method'
                % self.prog_name)

    def collect_job_output(self, batch):
        '''
        Not implemented.
        '''
        raise NotImplementedError(
                '"%s" object has no "collect_job_output" method'
                % self.prog_name)

    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        '''
        Not implemented.
        '''
        raise NotImplementedError(
                    '"%s" object has no "apply_statistics" method'
                    % self.prog_name)
