import os
import re
import subprocess

import tmlib.models
from tmlib.utils import notimplemented
from tmlib.workflow.api import ClusterRoutines


class MetadataExtractor(ClusterRoutines):

    '''Class for extraction of metadata from microscopic image files.

    Extracted metadata is formatted according to the
    `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.
    '''

    def __init__(self, experiment_id, step_name, verbosity, **kwargs):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        step_name: str
            name of the corresponding step
        verbosity: int
            logging level
        **kwargs: dict
            ignored keyword arguments
        '''
        super(MetadataExtractor, self).__init__(
            experiment_id, step_name, verbosity
        )

    @staticmethod
    def _get_ome_xml_filename(image_filename):
        return re.sub(
            r'(%s)$' % os.path.splitext(image_filename)[1],
            '.ome.xml', image_filename
        )

    def create_batches(self, args):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.steps.metaextract.args.MetaextractArgs
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict]]
            job descriptions
        '''
        job_descriptions = dict()
        job_descriptions['run'] = list()
        count = 0
        with tmlib.models.utils.Session() as session:
            for acq in session.query(tmlib.models.Acquisition).\
                    join(tmlib.models.Plate).\
                    join(tmlib.models.Experiment).\
                    filter(tmlib.models.Experiment.id == self.experiment_id):

                batches = self._create_batches(
                    acq.microscope_image_files, args.batch_size
                )

                job_indices = list()
                for j, files in enumerate(batches):
                    count += 1
                    job_indices.append(count-1)
                    job_descriptions['run'].append({
                        'id': count,
                        'inputs': {
                            'microscope_image_files': [
                                f.location for f in files
                            ]
                        },
                        'outputs': dict(),
                        'microscope_image_file_ids': [
                            f.id for f in files
                        ]
                    })

        return job_descriptions

    def run_job(self, batch):
        '''Extract OMEXML from microscope image or metadata files.

        Parameters
        ----------
        batch: dict
            description of the *run* job

        Note
        ----
        The actual processing is delegated to the
       `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_
        Bioformats command line tool.

        Raises
        ------
        subprocess.CalledProcessError
            when extraction failed
        '''
        for fid in batch['microscope_image_file_ids']:
            with tmlib.models.utils.Session() as session:
                img_file = session.query(tmlib.models.MicroscopeImageFile).\
                    get(fid)
                # The "showinf" command line tool writes the extracted OMEXML
                # to standard output.
                command = [
                    'showinf', '-omexml-only', '-nopix', '-novalid',
                    '-no-upgrade', img_file.location
                ]
                p = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = p.communicate()
                if p.returncode != 0 or not stdout:
                    raise subprocess.CalledProcessError(
                        'Extraction of OMEXML failed! Error message:\n%s'
                        % stderr
                    )

                img_file.omexml = stdout

    @notimplemented
    def collect_job_output(self, batch):
        pass
