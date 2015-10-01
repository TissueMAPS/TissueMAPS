import os
import logging
from .layers import ChannelLayer
from ..cluster import ClusterRoutines
from ..image import IllumstatsImages

logger = logging.getLogger(__name__)


class PyramidCreation(ClusterRoutines):

    def __init__(self, experiment, prog_name):
        '''
        Instantiate an instance of class PyramidCreation.

        Parameters
        ----------
        experiment: Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        '''
        super(PyramidCreation, self).__init__(experiment, prog_name)
        self.experiment = experiment
        self.prog_name = prog_name

    @property
    def shift_dirs(self):
        '''
        Returns
        -------
        List[str]
            name of directories, where shift descriptor files are stored
        '''
        self._shift_dirs = [c.shift_dir for c in self.cycles]
        return self._shift_dirs

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

    def create_job_descriptions(self, **kwargs):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        **kwargs: dict
            additional input arguments as key-value pairs:
            * "shift": whether images should be shifted (*bool*)
            * "illumcorr": whether images should be corrected for illumination
              artifacts (*bool*)
            * "thresh": whether images should be thresholded and rescaled
              (*bool*)
            * "thresh_value": fixed pixel value for threshold (*int*)
            * "thresh_percent": percentage of pixel values below threshold
              (*float*)
            * "stitch_only": whether the stitched image should be saved and
              no pyramid should be created (*bool*)

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        logger.debug('create descriptions for "run" jobs')
        joblist = dict()
        joblist['run'] = list()
        count = 0
        for i, cycle in enumerate(self.cycles):
            logger.debug('create job descriptions for cycle "%s"' % cycle.name)
            channels = list(set([md.channel for md in cycle.image_metadata]))
            img_batches = list()
            for c in channels:
                logger.debug('create job descriptions for channel "%s"' % c)
                image_files = [md.name for md in cycle.image_metadata
                               if md.channel == c]
                if len(image_files) == 0:
                    logger.warn(
                        'No image files found for cycle "%s" and channel "%s"'
                        % (cycle, c))
                img_batches.append(image_files)

            for j, batch in enumerate(img_batches):
                count += 1
                joblist['run'].append({
                    'id': count,
                    'inputs': {
                        'image_files': [
                            os.path.join(cycle.image_dir, f) for f in batch
                        ]
                    },
                    'outputs': {
                        'pyramid_dir':
                            os.path.join(self.experiment.layers_dir,
                                         '{cycle}_{channel}'.format(
                                                cycle=cycle.name,
                                                channel=channels[j]))
                    },
                    'channel': channels[j],
                    'cycle': cycle.name,
                    'shift': kwargs['shift'],
                    'illumcorr': kwargs['illumcorr'],
                    'thresh': kwargs['thresh'],
                    'thresh_value': kwargs['thresh_value'],
                    'thresh_percent': kwargs['thresh_percent']
                })
        return joblist

    def run_job(self, batch):
        '''
        Create 8bit greyscale JPEG zoomify pyramid layer of "channel" images.

        See also
        --------
        `illuminati.layers.ChannelLayer`_
        '''
        cycle = [c for c in self.cycles if c.name == batch['cycle']][0]

        if batch['illumcorr']:
            logger.info('correct images for illumination artifacts')
            stats_file, stats_metadata = [
                (os.path.join(cycle.stats_dir, md.filename), md)
                for md in cycle.stats_metadata
                if md.channel == batch['channel']
            ][0]
            stats = IllumstatsImages.create_from_file(
                        stats_file, stats_metadata)
        else:
            stats = None

        if batch['shift']:
            logger.info('align images between cycles')
            shift = cycle.shift_descriptions
        else:
            shift = None

        logger.debug('create channel layer')
        layer = ChannelLayer.create_from_files(
                    cycle=cycle, channel=batch['channel'],
                    stats=stats, shift=shift)

        if batch['thresh']:
            logger.info('threshold intensities')
            layer = layer.clip(thresh_value=batch['thresh_value'],
                               thresh_percent=batch['thresh_percent'])

        layer = layer.scale()

        output_dir = batch['outputs']['pyramid_dir']
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        logger.info('create image pyramid: %s' % output_dir)
        layer.create_pyramid(output_dir)

    def collect_job_output(self, batch):
        raise AttributeError('"%s" object doesn\'t have a "collect_job_output"'
                             ' method' % self.__class__.__name__)

    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
