import os
import re
import logging
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
        self._reg_file_format_string = '{experiment}_{job}.reg'
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
            ht = cycle.image_metadata_hashtable.sort('site_id')
            ix = ht['channel_id'] == kwargs['ref_channel']
            return ht[ix]['name'].tolist()

        im_batches = [
            self._create_batches(get_targets(c), kwargs['batch_size'])
            for c in self.cycles
        ]
        ht = self.cycles[0].image_metadata_hashtable
        ix = ht['channel_id'] == kwargs['ref_channel']
        sites = ht[ix]['site_id'].tolist()
        site_batches = self._create_batches(sites, kwargs['batch_size'])
        # def get_refs(cycle):
        #     if any([md.plane_id > 1 for md in cycle.image_metadata]):
        #         raise NotSupportedError(
        #                 'Alignment is only supported for 2D datasets.')
        #     return [
        #         f for i, f in enumerate(cycle.image_files)
        #         if cycle.image_metadata[i].channel_id == kwargs['ref_channel']
        #     ]
        # im_batches = [self._create_batches(natsorted(get_refs(c)), kwargs['batch_size'])
        #               for c in self.cycles]
        # # TODO: 3D
        # sites = [md.site_id for md in self.cycles[0].image_metadata
        #          if md.channel_id == kwargs['ref_channel']]
        # site_batches = self._create_batches(sites, kwargs['batch_size'])
        # TODO: create batches in such a way that all focal planes of the
        # same site end up in the same batch; required to do MIP on the fly
        registration_batches = list()
        for i in xrange(len(im_batches[0])):
            if any([i >= len(b) for b in im_batches]):
                continue
            registration_batches.append({
                'targets': {c.name: [
                        os.path.join(c.image_dir, b)
                        for b in im_batches[j][i]
                    ]
                    for j, c in enumerate(self.cycles)
                },
                'references': [
                    os.path.join(c.image_dir, b)
                    for j, c in enumerate(self.cycles)
                    if c.id == kwargs['ref_cycle']
                    for b in im_batches[j][i]
                ]
            })

        registration_files = [
            os.path.join(self.registration_dir,
                         self.reg_file_format_string.format(
                            experiment=self.experiment.name, job=i+1))
            for i in xrange(len(registration_batches))
        ]

        job_descriptions = {
            'run': [{
                'id': i+1,
                'inputs': {
                    'target_files': batch['targets'],
                    'reference_files': batch['references']
                },
                'outputs': {
                    'registration_files': [registration_files[i]]
                },
                'sites': site_batches[i]
            } for i, batch in enumerate(registration_batches)],
            'collect': {
                'max_shift': kwargs['max_shift'],
                'ref_cycle': kwargs['ref_cycle'],
                'inputs': {
                    'registration_files': registration_files
                },
                'outputs': {
                    'align_descriptor_files': [
                        os.path.join(c.dir, c.align_descriptor_file)
                        for c in self.experiment.cycles
                    ]
                }
            }
        }

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
        output_files = batch['inputs']['registration_files']
        cycle_names = [c.name for c in self.cycles]

        descriptions = reg.fuse_registration(output_files, cycle_names)

        # Calculate overhang between cycles
        upper_oh, lower_oh, right_oh, left_oh, dont_shift = \
            reg.calculate_overhang(descriptions, batch['max_shift'])

        with JsonWriter() as writer:
            for i, cycle in enumerate(self.cycles):
                logger.info('collect registration statistics for cycle %s'
                            % cycle.name)

                a = AlignmentDescription()
                a.cycle_id = cycle.id
                a.ref_cycle_id = batch['ref_cycle']

                a.overhang = OverhangDescription()
                a.overhang.lower = lower_oh
                a.overhang.upper = upper_oh
                a.overhang.right = right_oh
                a.overhang.left = left_oh

                a.shifts = list()

                for j in xrange(len(dont_shift)):

                    sh = ShiftDescription()
                    sh.x = descriptions[i][j]['x_shift']
                    sh.y = descriptions[i][j]['y_shift']
                    sh.site_id = descriptions[i][j]['site']
                    sh.is_above_max_shift = bool(dont_shift[j])

                    a.shifts.append(sh)

                logger.info('write alignment descriptor file')
                writer.write(batch['outputs']['align_descriptor_files'][i],
                             a.serialize())

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
                        if image.metadata.site_id not in sites:
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
