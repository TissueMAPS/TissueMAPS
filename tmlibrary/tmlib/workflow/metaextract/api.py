# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
import re
import logging
import subprocess

from gc3libs.quantity import Duration, Memory

import tmlib.models as tm
from tmlib.workflow import register_step_api
from tmlib.utils import notimplemented
from tmlib.utils import same_docstring_as
from tmlib.errors import MetadataError
from tmlib.errors import WorkflowError
from tmlib.readers import JavaBridge, BFOmeXmlReader
from tmlib.workflow.api import WorkflowStepAPI

logger = logging.getLogger(__name__)


@register_step_api('metaextract')
class MetadataExtractor(WorkflowStepAPI):

    '''Class for extraction of metadata from microscopic image files.

    Extracted metadata is formatted according to the
    `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.
    '''

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        '''
        super(MetadataExtractor, self).__init__(experiment_id)

    @staticmethod
    def _get_ome_xml_filename(image_filename):
        return re.sub(
            r'(%s)$' % os.path.splitext(image_filename)[1],
            '.ome.xml', image_filename
        )

    def _get_run_job_args(self, **args):
        '''
        Set the environment so that the JVM can run.

        See `TmLibrary issue #34 <https://github.com/TissueMAPS/TmLibrary/issues/34>`_
        for more information.
        '''
        args['environment'] = {
                # *note:* the following flags require JVM >= 8
                'BF_FLAGS': '-XX:+PrintGCDetails -XX:+PrintGCTimeStamps -XX:+UseSerialGC -XX:-UseCompressedOops -XX:-UseCompressedClassPointers',
            }
        return args

    def create_run_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.workflow.metaextract.args.MetaextractBatchArguments
            step-specific arguments

        Returns
        -------
        generator
            job descriptions
        '''
        count = 0

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            for acq in session.query(tm.Acquisition):
                n_files = session.query(tm.MicroscopeImageFile.id).\
                    filter_by(acquisition_id=acq.id).\
                    count()
                if n_files == 0:
                    raise WorkflowError(
                        'Acquisition "%s" of plate "%s" doesn\'t have any '
                        'microscope image files. Did you delete them in a '
                        'previous submission or forgot to upload them?' % (
                            acq.name, acq.plate.name
                        )
                    )
                microscope_image_files = session.query(
                        tm.MicroscopeImageFile.id
                    ).\
                    filter_by(acquisition_id=acq.id).\
                    all()
                microscope_image_file_ids = [
                    f.id for f in microscope_image_files
                ]
                batches = self._create_batches(
                    microscope_image_file_ids, args.batch_size
                )

                for file_ids in batches:
                    count += 1
                    yield {
                        'id': count,
                        'microscope_image_file_ids': file_ids
                    }

    @same_docstring_as(WorkflowStepAPI.delete_previous_job_output)
    def delete_previous_job_output(self):
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            logger.debug(
                'set attribute "omexml" of instances of class '
                'tmlib.models.MicroscopeImageFile to None'
            )
            files = session.query(tm.MicroscopeImageFile.id)
            session.bulk_update_mappings(
                tm.MicroscopeImageFile,
                [{'id': f.id, 'omexml': None} for f in files]
            )

    def run_job(self, batch, assume_clean_state=False):
        '''Extracts OMEXML from microscope image or metadata files.

        Parameters
        ----------
        batch: dict
            description of the *run* job
        assume_clean_state: bool, optional
            assume that output of previous runs has already been cleaned up

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
        # NOTE: Ideally, we would use the BFOmeXmlReader together with JavaBridge
        # but this approach has several shortcomings and requires too much
        # memory to run efficiently on individual cores.
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            for fid in batch['microscope_image_file_ids']:
                img_file = session.query(tm.MicroscopeImageFile).get(fid)
                logger.info('process image %d' % img_file.id)
                # The "showinf" command line tool writes the extracted OMEXML
                # to standard output.
                command = [
                    'showinf', '-omexml-only', '-nopix', '-novalid', '-nocore',
                    '-no-upgrade', '-no-sas', img_file.location
                ]
                p = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = p.communicate()
                logger.debug("showinf STDOUT: \n```%s```\n", stdout)
                logger.debug("showinf STDERR: \n```%s```\n", stderr)
                if p.returncode != 0 or not stdout:
                    raise MetadataError(
                        'Extraction of OMEXML failed! Error message:\n%s'
                        % stderr
                    )
                # the OME-XML data is contained within XML tags `<OME ...>` and `</OME>`
                start = stdout.find("<OME")
                if start == -1:
                    raise ValueError("Cannot find OME-XML start tag in `showinf` output.")
                end = stdout.rfind("</OME>", start)
                if end == -1:
                    raise ValueError("Cannot find OME-XML closing tag in `showinf` output.")
                img_file.omexml = unicode(stdout[start : end+len('</OME>')])
                session.add(img_file)
                session.commit()
                session.expunge(img_file)

    @notimplemented
    def collect_job_output(self, batch):
        pass
