import os
import re
import logging
import shutil
import numpy as np
from . import registration as reg
from .description import AlignmentDescription
from .description import OverhangDescription
from .description import ShiftDescription
from ..writers import JsonWriter
from ..api import ClusterRoutines
from ..errors import NotSupportedError

logger = logging.getLogger(__name__)


class ImageRegistration(ClusterRoutines):

    def __init__(self, experiment, prog_name, verbosity):
        '''
        Initialize an instance of class ImageRegistration.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
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

    def create_job_descriptions(self, args):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.align.args.AlignInitArgs
            program-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        def get_targets(cycle):
            md = cycle.image_metadata.sort_values('site_ix')
            ix = md['channel_ix'] == args.ref_channel
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
                'align_descriptor_files': list()
            },
            'removals': ['registration_files']
        }
        for plate in self.experiment.plates:
            md = plate.cycles[0].image_metadata.sort_values('site_ix')
            if len(np.unique(md['zplane_ix'])) > 1:
                raise NotSupportedError(
                    'Alignment is currently only supported for 2D datasets.')
            # TODO: group images per site
            # (such that all z-planes end up in the same batch)
            im_batches = [
                self._create_batches(get_targets(c), args.batch_size)
                for c in plate.cycles
            ]

            ix = md['channel_ix'] == args.ref_channel
            sites = md[ix]['site_ix'].tolist()
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
            jdc['plates'].append(plate.name)
            jdc['inputs']['registration_files'].append(registration_files)
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
        for i, plate_name in enumerate(batch['plates']):
            plate = [
                p for p in self.experiment.plates if p.name == plate_name
            ][0]

            reg_files = batch['inputs']['registration_files'][i]
            cycle_folders = [os.path.basename(c.dir) for c in plate.cycles]

            descriptions = reg.fuse_registration(reg_files, cycle_folders)

            # Calculate overhang between cycles
            upper_oh, lower_oh, right_oh, left_oh, dont_shift = \
                reg.calculate_overhang(descriptions, batch['limit'])

            with JsonWriter() as writer:
                for j, cycle in enumerate(plate.cycles):
                    logger.info('collect registration statistics for cycle %s'
                                % cycle.index)

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

    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        '''
        Apply calculated statistics (shift and overhang values) to images
        in order to align them between cycles.

        Parameters
        ----------
        output_dir: str
            absolute path to directory where the processed images should be
            stored
        plates: List[str]
            plate names
        wells: List[str]
            well identifiers
        sites: List[int]
            site indices
        channels: List[str]
            channel indices
        tpoints: List[int]
            time point (cycle) indices
        zplanes: List[int]
            z-plane indices
        **kwargs: dict
            additional arguments as key-value pairs:
                * "illumcorr": to correct for illumination artifacts (*bool*)
        '''
        logger.info('align images between cycles')
        for plate in self.experiment.plates:
            if plates:
                if plate.name not in plates:
                    continue
            for cycle in plate.cycles:
                if tpoints:
                    if cycle.index not in tpoints:
                        continue
                md = cycle.image_metadata
                sld = md.copy()
                if sites:
                    sld = sld[sld['site_ix'].isin(sites)]
                if wells:
                    sld = sld[sld['well_name'].isin(wells)]
                if channels:
                    sld = sld[sld['channel_ix'].isin(channels)]
                if zplanes:
                    sld = sld[sld['zplane_ix'].isin(zplanes)]
                selected_channels = list(set(sld['channel_ix'].tolist()))
                for c in selected_channels:
                    if kwargs['illumcorr']:
                        stats = cycle.illumstats_images[c]
                    sld = sld[sld['channel_ix'] == c]
                    image_indices = sld['name'].index
                    for i in image_indices:
                        image = cycle.images[i]
                        filename = image.metadata.name
                        logger.info('align image: %s', filename)
                        suffix = os.path.splitext(image.metadata.name)[1]
                        if kwargs['illumcorr']:
                            image = image.correct(stats)
                            filename = re.sub(
                                r'\%s$' % suffix, '_corrected%s' % suffix,
                                filename)
                        aligned_image = image.align()
                        output_filename = re.sub(
                            r'\%s$' % suffix, '_aligned%s' % suffix,
                            filename)
                        output_filename = os.path.join(
                            output_dir, output_filename)
                        aligned_image.save(output_filename)
