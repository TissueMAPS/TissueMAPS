import os
import re
import numpy as np
from natsort import natsorted
from cached_property import cached_property
from . import registration as reg
from .. import utils
from ..cluster import ClusterRoutines
from ..shift import ShiftDescription
from ..image import ChannelImage
from ..image import IllumstatsImages


class ImageRegistration(ClusterRoutines):

    def __init__(self, experiment, shift_file_format_string,
                 prog_name, logging_level='critical'):
        '''
        Initialize an instance of class ImageRegistration.

        Parameters
        ----------
        experiment: Experiment
            experiment object that holds information about the content of
            one or more cycle directories
        shift_file_format_string: str
            format string that specifies how the name of the shift file
            should be formatted
        prog_name: str
            name of the corresponding program (command line interface)
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)

        See also
        --------
        `tmlib.cfg`_
        '''
        super(ImageRegistration, self).__init__(logging_level)
        self.experiment = experiment
        self.prog_name = prog_name
        if not os.path.exists(self.experiment.registration_dir):
            os.mkdir(self.experiment.registration_dir)
        self.shift_file_format_string = shift_file_format_string

    @property
    def log_dir(self):
        '''
        Returns
        -------
        str
            directory where log files should be stored

        Note
        ----
        The directory will be sibling to the output directory.
        '''
        self._log_dir = os.path.join(self.experiment.dir,
                                     'log_%s' % self.prog_name)
        return self._log_dir

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

    @property
    def shift_files(self):
        '''
        Returns
        -------
        List[str]
            absolute paths to the shift descriptor files
        '''
        self._shift_files = [os.path.join(c.shift_dir,
                                          self.shift_file_format_string.format(
                                                cycle=c.name))
                             for c in self.cycles]
        return self._shift_files

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

    def create_joblist(self, **kwargs):
        '''
        Create a joblist for parallel computing.

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
        def get_refs(x):
            return [f for i, f in enumerate(x.image_files)
                    if x.image_metadata[i].channel == kwargs['ref_channel']]
        im_batches = [self._create_batches(get_refs(c), kwargs['batch_size'])
                      for c in self.cycles]
        sites = [md.site for md in self.cycles[0].image_metadata
                 if md.channel == kwargs['ref_channel']]
        site_batches = self._create_batches(sites, kwargs['batch_size'])
        registration_batches = list()
        for i in xrange(len(im_batches[0])):
            if any([i >= len(b) for b in im_batches]):
                continue
            registration_batches.append({
                'targets':
                    {c.name: [os.path.join(c.image_dir, b)
                              for b in im_batches[j][i]]
                     for j, c in enumerate(self.cycles)},
                'references':
                    [os.path.join(c.image_dir, b)
                     for j, c in enumerate(self.cycles)
                     if c.name == kwargs['ref_cycle']
                     for b in im_batches[j][i]]
            })

        registration_files = [os.path.join(self.experiment.registration_dir,
                                           self.reg_file_format_string.format(
                                            experiment=self.experiment.name,
                                            job=i+1))
                              for i in xrange(len(registration_batches))]

        joblist = {
            'run': [{
                'id': i+1,
                'inputs': {
                    'image_files': batch
                },
                'outputs': {
                    'registration_file': registration_files[i]
                },
                'sites': site_batches[i]
            } for i, batch in enumerate(registration_batches)],
            'collect': {
                'inputs': {
                    'registration_files': registration_files
                },
                'outputs': {
                    'shift_descriptor_files': self.shift_files
                }
            }
        }

        return joblist

    def _build_run_command(self, batch):
        job_id = batch['id']
        command = ['align']
        command.append(self.experiment.dir)
        command.extend(['run', '--job', str(job_id)])
        return command

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
        `align.registration.register_images`_
        '''
        reg.register_images(batch['sites'],
                            batch['inputs']['image_files']['targets'],
                            batch['inputs']['image_files']['references'],
                            batch['outputs']['registration_file'])

    def _build_collect_command(self):
        command = [self.prog_name]
        command.append(self.experiment.dir)
        command.extend(['collect'])
        return command

    def collect_job_output(self, batch, **kwargs):
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
        **kwargs: dict
            additional variable input arguments as key-value pairs:
            * "max_shift": shift value in pixels that is maximally tolerated,
              sites with larger shift values will be ignored (*int*)

        See also
        --------
        `align.registration.fuse_registration`_
        '''
        output_files = batch['inputs']['registration_files']
        cycle_names = [c.name for c in self.cycles]

        shift_descriptions = reg.fuse_registration(output_files, cycle_names)

        # Calculate overhang between cycles
        top, bottom, right, left, no_shift = \
            reg.calculate_overhang(shift_descriptions, kwargs['max_shift'])

        for i, cycle_name in enumerate(cycle_names):

            description = list()
            for j in xrange(len(no_shift)):

                shift = ShiftDescription()
                shift.lower_overhang = bottom
                shift.upper_overhang = top
                shift.right_overhang = right
                shift.left_overhang = left
                shift.max_shift = kwargs['max_shift']
                shift.omit = bool(no_shift[j])
                shift.cycle = self.cycles[i].name
                shift.filename = shift_descriptions[i][j]['filename']
                shift.x_shift = shift_descriptions[i][j]['x_shift']
                shift.y_shift = shift_descriptions[i][j]['y_shift']
                shift.site = shift_descriptions[i][j]['site']

                description.append(shift.serialize())

            # Sort entries according to site
            sites = [(d['site'], j) for j, d in enumerate(description)]
            order = np.array(natsorted(sites))
            description = [description[j] for j in order[:, 1]]

            shift_file = batch['outputs']['shift_descriptor_files'][i]
            utils.write_json(shift_file, description)

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
            cycle.image_files
            cycle.image_metadata
            cycle.image_shifts
            for channel in channels:
                channel_index = [i for i, md in enumerate(cycle.image_metadata)
                                 if md.channel == channel]
                if not channel_index:
                    raise ValueError('Channel name is not valid: %s' % channel)
                channel_images = [ChannelImage.create_from_file(
                                    os.path.join(cycle.image_dir,
                                                 cycle.image_files[ix]))
                                  for ix in channel_index]
                shifts = [cycle.image_shifts[ix] for ix in channel_index]
                if kwargs['illumcorr']:
                    ix = [i for i, md in enumerate(cycle.stats_metadata)
                          if md.channel == channel]
                    stats = IllumstatsImages.create_from_file(
                                cycle.stats_files[ix])

                for i, image in enumerate(channel_images):
                    if sites:
                        if image.metadata.site not in sites:
                            continue
                    if wells:
                        if not image.metadata.well:  # may not be a well plate
                            continue
                        if image.metadata.well not in wells:
                            continue
                    suffix = os.path.splitext(image.metadata.name)[1]
                    if kwargs['illumcorr']:
                        image = image.correct(stats.mean, stats.std)
                        output_filename = re.sub(r'\%s$' % suffix,
                                                 '_corrected_aligned%s' % suffix,
                                                 image.metadata.name)
                    else:
                        output_filename = re.sub(r'\%s$' % suffix,
                                                 '_aligned%s' % suffix,
                                                 image.metadata.name)
                    aligned_image = image.align(shifts[i])
                    output_filename = os.path.join(output_dir, output_filename)
                    aligned_image.save_as_png(output_filename)
