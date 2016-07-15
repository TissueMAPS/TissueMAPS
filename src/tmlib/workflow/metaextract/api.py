import os
import re
import logging
import subprocess

import tmlib.models
from tmlib.workflow import register_api
from tmlib.utils import notimplemented
from tmlib.utils import same_docstring_as
from tmlib.errors import MetadataError
from tmlib.workflow.api import ClusterRoutines

logger = logging.getLogger(__name__)


@register_api('metaextract')
class MetadataExtractor(ClusterRoutines):

    '''Class for extraction of metadata from microscopic image files.

    Extracted metadata is formatted according to the
    `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.
    '''

    def __init__(self, experiment_id, verbosity, **kwargs):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging level
        **kwargs: dict
            ignored keyword arguments
        '''
        super(MetadataExtractor, self).__init__(experiment_id, verbosity)

    @staticmethod
    def _get_ome_xml_filename(image_filename):
        return re.sub(
            r'(%s)$' % os.path.splitext(image_filename)[1],
            '.ome.xml', image_filename
        )

    def create_batches(self, args):
        '''Creates job descriptions for parallel computing.

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

                if not acq.microscope_image_files:
                    raise ValueError(
                        'Experiment doesn\'t have any microscope image files'
                    )
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

    @same_docstring_as(ClusterRoutines.delete_previous_job_output)
    def delete_previous_job_output(self):
        with tmlib.models.utils.Session() as session:
            files = session.query(tmlib.models.MicroscopeImageFile).\
                join(tmlib.models.Acquisition).\
                join(tmlib.models.Plate).\
                filter(tmlib.models.Plate.experiment_id == self.experiment_id).\
                all()

            # Set value in "omexml" column to NULL
            logger.debug(
                'set attribute "omexml" of instances of class '
                'tmlib.models.MicroscopeImageFile to None'
            )
            for f in files:
                f.omexml = None
            session.add_all(files)

    def run_job(self, batch):
        '''Extracts OMEXML from microscope image or metadata files.

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
        with tmlib.models.utils.Session() as session:
            for fid in batch['microscope_image_file_ids']:
                img_file = session.query(tmlib.models.MicroscopeImageFile).\
                    get(fid)
                logger.info('process image "%s"' % img_file.name)
                # The "showinf" command line tool writes the extracted OMEXML
                # to standard output.
                command = [
                    'showinf', '-omexml-only', '-nopix', '-novalid',
                    '-no-upgrade', '-no-sas', img_file.location
                ]
                p = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = p.communicate()
                if p.returncode != 0 or not stdout:
                    raise MetadataError(
                        'Extraction of OMEXML failed! Error message:\n%s'
                        % stderr
                    )
                try:
                    omexml = re.search(
                        r'<(\w+).*</\1>', stdout, flags=re.DOTALL
                    ).group()
                except:
                    raise RegexError(
                        'OMEXML metadata could not be extracted.'
                    )
                img_file.omexml = unicode(omexml)

    @notimplemented
    def collect_job_output(self, batch):
        pass

