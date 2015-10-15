import os
import re
import logging
import shutil
import numpy as np
from . import registration as reg
from .descriptions import AlignmentDescription
from .descriptions import OverhangDescription
from .descriptions import ShiftDescription
from ..writers import JsonWriter
from ..cluster import ClusterRoutines
from ..image import ChannelImage
from ..errors import NotSupportedError

logger = logging.getLogger(__name__)


class ImageRegistration(ClusterRoutines):

    def __init__(self, experiment, prog_name, verbosity):
        '''
        Initialize an instance of class ImageRegistration.

        Parameters
        ----------
        experiment: Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level
        '''
        super(ImageRegistration, self).__init__(
                experiment, prog_name, verbosity)
        self.experiment = experiment
        self.prog_name = prog_name
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
        self._registration_dir = os.path.join(self.project_dir, 'registration')
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

    def create_job_descriptions(self, **kwargs):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        **kwargs: dict
            additional input arguments as key-value pairs:
            * "batch_size": number of image acquisition sites per job (*int*)
            * "ref_channel": number of the image channel that should be used as
              a reference for image registration (*int*)
            * "ref_cycle": number of the image channel that should be used as a
              reference for image registration (*int*)

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        def get_targets(cycle):
            md = cycle.image_metadata_table.sort('site_ix')
            ix = md['channel_ix'] == kwargs['ref_channel']
            return md[ix]['name'].tolist()

        job_count = 0
        job_descriptions = dict()
        job_descriptions['run'] = list()
        job_descriptions['collect'] = {
            'plates': list(),
            'limit': kwargs['limit'],
            'ref_cycle': kwargs['ref_cycle'],
            'inputs': {
                'registration_files': list()
            },
            'outputs': {
                'align_descriptor_files': list()
            }
        }
        for plate in self.experiment.plates:
            md = plate.cycles[0].image_metadata_table
            if len(np.unique(md['zplane_ix'])) > 1:
                raise NotSupportedError(
                    'Alignment is currently only supported for 2D datasets.')
            # TODO: group images per site
            # (such that all z-planes end up in the same batch)
            im_batches = [
                self._create_batches(get_targets(c), kwargs['batch_size'])
                for c in plate.cycles
            ]
            
            ix = md['channel_ix'] == kwargs['ref_channel']
            sites = md[ix]['site_ix'].tolist()
            site_batches = self._create_batches(sites, kwargs['batch_size'])
            
            registration_batches = list()
            for i in xrange(len(im_batches[0])):
                if any([i >= len(b) for b in im_batches]):
                    continue
                registration_batches.append({
                    'targets': {c.name: [
                            os.path.join(c.image_dir, b)
                            for b in im_batches[j][i]
                        ]
                        for j, c in enumerate(plate.cycles)
                    },
                    'references': [
                        os.path.join(c.image_dir, b)
                        for j, c in enumerate(plate.cycles)
                        if c.index == kwargs['ref_cycle']
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
            jdc['plates'].append(plate.name)
            jdc['inputs']['registration_files'].append(
                registration_files
            )
            jdc['outputs']['align_descriptor_files'].append([
                os.path.join(c.dir, c.align_descriptor_file)
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
        `tmlib.align.registration.register_images`_
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
        `tmlib.align.registration.fuse_registration`_
        '''
        for i, plate_name in enumerate(batch['plates']):
            plate = [
                p for p in self.experiment.plates if p.name == plate_name
            ][0]

            reg_files = batch['inputs']['registration_files'][i]
            cycle_names = [c.name for c in plate.cycles]

            descriptions = reg.fuse_registration(reg_files, cycle_names)

            # Calculate overhang between cycles
            upper_oh, lower_oh, right_oh, left_oh, dont_shift = \
                reg.calculate_overhang(descriptions, batch['limit'])

            with JsonWriter() as writer:
                for j, cycle in enumerate(plate.cycles):
                    logger.info('collect registration statistics for cycle %s'
                                % cycle.name)

                    a = AlignmentDescription()
                    a.cycle_ix = cycle.index
                    a.ref_cycle_ix = batch['ref_cycle']

                    a.overhang = OverhangDescription()
                    a.overhang.lower = lower_oh
                    a.overhang.upper = upper_oh
                    a.overhang.right = right_oh
                    a.overhang.left = left_oh

                    a.shifts = list()
                    for k in xrange(len(dont_shift)):

                        sh = ShiftDescription()
                        sh.x = descriptions[j][k]['x_shift']
                        sh.y = descriptions[j][k]['y_shift']
                        sh.site_ix = descriptions[j][k]['site']
                        sh.is_above_limit = bool(dont_shift[k])

                        a.shifts.append(sh)

                    logger.info('write alignment descriptor file')
                    writer.write(
                        batch['outputs']['align_descriptor_files'][i][j],
                        dict(a))

            logger.info('remove registration files')
            reg_dir = os.path.dirname(reg_files[0])
            logger.debug('remove directory: %s', reg_dir)
            shutil.rmtree(reg_dir)

    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
        '''
        Apply calculated statistics (shift and overhang values) to images
        in order to align them between cycles.

        Parameters
        ----------
        wells: List[str]
            well identifiers of images that should be aligned
        sites: List[int]
            one-based site indices of images that should be aligned
        channels: List[str]
            channel names of images that should be aligned
        output_dir: str
            absolute path to directory where the aligned images should be
            stored
        **kwargs: dict
            additional variable input arguments as key-value pairs:
            * "illumcorr": also correct illumination artifacts (*bool*)
        '''
        for cycle in self.cycles:
            for channel in channels:
                channel_index = [
                    i for i, md in enumerate(cycle.image_metadata)
                    if md.channel_name == channel
                ]
                if not channel_index:
                    raise ValueError('Channel name is not valid: %s' % channel)
                channel_images = [
                    ChannelImage.create_from_file(
                        os.path.join(cycle.image_dir, cycle.image_files[ix]),
                        cycle.image_metadata[ix])
                    for ix in channel_index
                ]
                if kwargs['illumcorr']:
                    stats = [
                        stats for stats in cycle.illumstats_images
                        if stats.metadata.channel_name == channel
                    ][0]

                for i, image in enumerate(channel_images):
                    if sites:
                        if image.metadata.site_ix not in sites:
                            continue
                    if wells:
                        if not image.metadata.well_id:  # may not be a well plate
                            continue
                        if image.metadata.well_id not in wells:
                            continue
                    suffix = os.path.splitext(image.metadata.name)[1]
                    if kwargs['illumcorr']:
                        image = image.correct(stats)
                        output_filename = re.sub(
                            r'\%s$' % suffix, '_corrected_aligned%s' % suffix,
                            image.metadata.name)
                    else:
                        output_filename = re.sub(
                            r'\%s$' % suffix, '_aligned%s' % suffix,
                            image.metadata.name)
                    aligned_image = image.align()
                    output_filename = os.path.join(output_dir, output_filename)
                    aligned_image.save_as_png(output_filename)
