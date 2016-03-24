import os
import re
import logging
import shutil
import numpy as np
import pandas as pd
from . import registration as reg
from ..writers import DataTableWriter
from ..api import ClusterRoutines
from ..errors import NotSupportedError

logger = logging.getLogger(__name__)


class ImageRegistration(ClusterRoutines):

    '''
    Class for registering and aligning images between cycles.

    Note
    ----
    Alignment is so far only supported for 2D image datasets.
    '''

    def __init__(self, experiment, step_name, verbosity, **kwargs):
        '''
        Initialize an instance of class ImageRegistration.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        step_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level
        kwargs: dict
            additional arguments in form of key-value pairs (ignored)
        '''
        super(ImageRegistration, self).__init__(
                experiment, step_name, verbosity)
        self.experiment = experiment
        self.step_name = step_name
        self.verbosity = verbosity

    @property
    def registration_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the folder holding the calculated shift values
            of the image registration step
        '''
        self._registration_dir = os.path.join(self.step_location, 'registration')
        if not os.path.exists(self._registration_dir):
            os.mkdir(self._registration_dir)
        return self._registration_dir

    @property
    def reg_file_format_string(self):
        '''
        Returns
        -------
        str
            format string for names of HDF5 files, where registration outputs
            are stored
        '''
        self._reg_file_format_string = '{experiment}_{job}.reg.h5'
        return self._reg_file_format_string

    def create_batches(self, args):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.align.args.AlignInitArgs
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions

        Raises
        ------
        tmlib.errors.NotSupportedError
            when a plate contains only one cycle or when the image dataset is
            3 dimensional, i.e. when there is more than one z-plane
        ValueError  
            when `args.ref_channel` does not exist across all cycles
        '''
        def get_targets(cycle):
            md = cycle.image_metadata.sort_values('site')
            ix = md['channel_name'] == args.ref_channel
            return md[ix]['name'].tolist()

        job_count = 0
        job_descriptions = dict()
        job_descriptions['run'] = list()
        job_descriptions['collect'] = {
            'plates': list(),
            'limit': args.limit,
            'ref_cycle': args.ref_cycle,
            'inputs': {
                'registration_files': list()
            },
            'outputs': {
                'metadata_files': list()
            }
        }
        for plate in self.experiment.plates:
            if len(plate.cycles) == 1:
                raise NotSupportedError(
                            'Alignment requires more than one cycle, but '
                            'plate #%d contains only one cycle.' % plate.index)
            md = plate.cycles[0].image_metadata.sort_values('site')
            if len(np.unique(md['zplane'])) > 1:
                raise NotSupportedError(
                    'Alignment is currently only supported for 2D datasets.')
            # TODO: group images per site such that all z-planes will end up
            # in the same batch.
            # This might be necessary to align 3D stacks where MIPs should
            # probably be used for the registration rather than the individual
            # z-planes, since individual planes could be empty and that will
            # screw up the registration.
            im_batches = [
                self._create_batches(get_targets(c), args.batch_size)
                for c in plate.cycles
            ]
            # Ensure that the provided reference channel actually exists
            # across all cycles
            for cycle in plate.cycles:
                cycle_md = cycle.image_metadata
                if not any(cycle_md.channel_name == args.ref_channel):
                    raise ValueError(
                            'Channel "%s" does not exist in cycle #%d.'
                            % (args.ref_channel, cycle.index))
            ix = md['channel_name'] == args.ref_channel
            sites = md[ix]['site'].tolist()
            site_batches = self._create_batches(sites, args.batch_size)

            registration_batches = list()
            for i in xrange(len(im_batches[0])):
                if any([i >= len(b) for b in im_batches]):
                    continue
                registration_batches.append({
                    'targets': {os.path.basename(c.dir): [
                            os.path.join(c.image_dir, b)
                            for b in im_batches[j][i]
                        ]
                        for j, c in enumerate(plate.cycles)
                    },
                    'references': [
                        os.path.join(c.image_dir, b)
                        for j, c in enumerate(plate.cycles)
                        if c.index == args.ref_cycle
                        for b in im_batches[j][i]
                    ]
                })

            registration_files = [
                os.path.join(self.registration_dir,
                             self.reg_file_format_string.format(
                                experiment=self.experiment.name, job=i+1))
                for i in xrange(len(registration_batches))
            ]

            for i, batch in enumerate(registration_batches):
                job_count += 1
                job_descriptions['run'].append({
                        'id': job_count,
                        'inputs': {
                            'target_files': batch['targets'],
                            'reference_files': batch['references']
                        },
                        'outputs': {
                            'registration_files': [registration_files[i]]
                        },
                        'sites': site_batches[i]
                })

            jdc = job_descriptions['collect']
            jdc['plates'].append(plate.index)
            jdc['inputs']['registration_files'].append(registration_files)
            jdc['outputs']['metadata_files'].append([
                os.path.join(c.dir, c.metadata_file)
                for c in plate.cycles
            ])

        return job_descriptions

    def run_job(self, batch):
        '''
        Run shift and overhang calculation for a single job.

        Creates for a `.registration` HDF5 file, where calculated
        shift and overhang values are stored.

        Parameters
        ----------
        batch: dict
            description of the *run* job

        See also
        --------
        :py:func:`tmlib.align.registration.register_images`
        '''
        reg.register_images(batch['sites'],
                            batch['inputs']['target_files'],
                            batch['inputs']['reference_files'],
                            batch['outputs']['registration_files'][0])

    def collect_job_output(self, batch):
        '''
        Collect and fuse shift calculations and create shift description file.

        Reads the `.registration` HDF5 file created in the `run` step,
        concatenates the calculated shift values, calculates global overhang
        values and stores these values together with additional metainformation
        in YAML format.

        Parameters
        ----------
        batch: dict
            description of the *collect* job

        See also
        --------
        :py:func:`tmlib.align.registration.fuse_registration`
        '''
        for i, plate in enumerate(batch['plates']):
            plate = self.experiment.plates[plate]

            reg_files = batch['inputs']['registration_files'][i]
            cycle_folders = [os.path.basename(c.dir) for c in plate.cycles]

            shift_description = reg.fuse_registration(reg_files, cycle_folders)

            # Calculate overhang between cycles
            upper_oh, lower_oh, right_oh, left_oh, dont_shift = \
                reg.calculate_overhang(shift_description, batch['limit'])

            for j, cycle in enumerate(plate.cycles):
                logger.info(
                        'collect registration statistics for cycle %s'
                        % cycle.index)

                overhangs = pd.DataFrame()
                overhangs['upper'] = pd.Series(upper_oh)
                overhangs['lower'] = pd.Series(lower_oh)
                overhangs['right'] = pd.Series(right_oh)
                overhangs['left'] = pd.Series(left_oh)

                x_shifts = list()
                y_shifts = list()
                sites = list()
                is_above_limit = list()
                for k in xrange(len(dont_shift)):
                    x_shifts.append(shift_description[j][k]['x_shift'])
                    y_shifts.append(shift_description[j][k]['y_shift'])
                    sites.append(shift_description[j][k]['site'])
                    is_above_limit.append(bool(dont_shift[k]))

                shifts = pd.DataFrame()
                shifts['x'] = pd.Series(x_shifts)
                shifts['y'] = pd.Series(y_shifts)
                shifts['site'] = pd.Series(sites)
                shifts['is_above_limit'] = pd.Series(is_above_limit)

                logger.info('write alignment description to file')
                filename = batch['outputs']['metadata_files'][0][j]
                with DataTableWriter(filename) as writer:
                    writer.write('overhangs', overhangs)
                    writer.write('shifts', shifts)

            logger.info('remove intermediate registration files')
            reg_dir = os.path.dirname(reg_files[0])
            logger.debug('remove directory: %s', reg_dir)
            shutil.rmtree(reg_dir)
