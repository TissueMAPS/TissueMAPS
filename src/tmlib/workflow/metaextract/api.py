import os
import re

import tmlib.models
from tmlib.utils import flatten
from tmlib.workflow.api import ClusterRoutines
from tmlib.errors import WorkflowError


class MetadataExtractor(ClusterRoutines):

    '''Class for extraction of metadata from microscopic image files.

    Extracted metadata is formatted according to the
    `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_
    and written to XML files.
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
        kwargs: dict
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
        job_descriptions['collect'] = {
            'inputs': {
                'omexml_files': list()
            },
            'outputs': dict(),
        }
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
                            'image_files': [
                                os.path.join(
                                    acq.microscope_images_location, f.name
                                )
                                for f in files
                            ]
                        },
                        'outputs': {
                            'omexml_files': [
                                os.path.join(
                                    acq.omexml_location,
                                    self._get_ome_xml_filename(f.name)
                                )
                                for f in files
                            ]
                        }
                    })

                job_descriptions['collect']['inputs']['omexml_files'].append(
                    flatten([
                        job_descriptions['run'][j]['outputs']['omexml_files']
                        for j in job_indices
                    ])
                )

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
        actual processing is done via the
       `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_
        Bioformats command line tool.
        '''
        raise NotImplementedError(
            '"%s" object has no "run_job" method' % self.step_name
        )

    def collect_job_output(self, batch):
        '''
        Register the created files in the database.

        Parameters
        ----------
        batch: dict
            job description

        Raises
        ------
        :py:class:`tmlib.errors.WorkflowError`
            when an expected file does not exist, i.e. was not created
        '''
        with tmlib.models.utils.Session() as session:
            acquisitions = session.query(tmlib.models.Acquisition).\
                join(tmlib.models.Plate).\
                join(tmlib.models.Experiment).\
                filter(tmlib.models.Experiment.id == self.experiment_id).\
                all()
            for i, acq in enumerate(acquisitions):
                for f in batch['inputs']['omexml_files'][i]:
                    filename = os.path.basename(f)
                    if not os.path.exists(f):
                        raise WorkflowError(
                            'OMEXML file "%s" was not created!' % filename
                        )

                    session.get_or_create(
                        tmlib.models.OmeXmlFile,
                        name=filename, acquisition_id=acq.id
                    )
