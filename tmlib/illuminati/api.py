import os
import logging
import numpy as np
from .layers import ChannelLayer
from ..cluster import ClusterRoutines

logger = logging.getLogger(__name__)


class PyramidBuilder(ClusterRoutines):

    def __init__(self, experiment, prog_name, verbosity):
        '''
        Initialize an instance of class PyramidBuilder.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level

        Returns
        -------
        tmlib.illuminati.api.PyramidBuilder
        '''
        super(PyramidBuilder, self).__init__(experiment, prog_name, verbosity)
        self.experiment = experiment
        self.prog_name = prog_name
        self.verbosity = verbosity

    def create_job_descriptions(self, **kwargs):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        **kwargs: dict
            additional arguments as key-value pairs:
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
        job_descriptions = dict()
        job_descriptions['run'] = list()
        job_count = 0
        for plate in self.experiment.plates:
            for i, cycle in enumerate(plate.cycles):
                md = cycle.image_metadata_table
                channels = np.unique(md['channel_ix'])
                zplanes = np.unique(md['zplane_ix'])
                batch_indices = list()
                for c in channels:
                    for z in zplanes:
                        ix = (md['channel_ix'] == c) & (md['zplane_ix'] == z)
                        if len(ix) == 0:
                            logger.warn(
                                'No image files found for cycle "%s", '
                                'channel "%s" and plane "%d"'
                                % (cycle.index, c, z))
                        batch_indices.append(md[ix].index.tolist())

                for j, indices in enumerate(batch_indices):
                    image_files = md.loc[indices]['name']
                    channel = np.unique(md.loc[indices]['channel_ix'])[0]
                    zplane = np.unique(md.loc[indices]['zplane_ix'])[0]
                    job_count += 1
                    job_descriptions['run'].append({
                        'id': job_count,
                        'inputs': {
                            'image_files': [
                                os.path.join(cycle.image_dir, f)
                                for f in image_files
                            ]
                        },
                        'outputs': {
                            'pyramid_dir':
                                os.path.join(
                                    self.experiment.layers_dir,
                                    self.experiment.layer_names[(
                                        cycle.index, channel, zplane)])
                        },
                        'cycle': cycle.index,
                        'channel': channel,
                        'zplane': zplane,
                        'shift': kwargs['shift'],
                        'illumcorr': kwargs['illumcorr'],
                        'thresh': kwargs['thresh'],
                        'thresh_value': kwargs['thresh_value'],
                        'thresh_percent': kwargs['thresh_percent']
                    })
        return job_descriptions

    def run_job(self, batch):
        '''
        Create 8-bit greyscale JPEG zoomify pyramid layer of "channel" images.

        See also
        --------
        `illuminati.layers.ChannelLayer`_
        '''
        logger.debug('create channel layer')
        layer = ChannelLayer.create_from_files(
                    experiment=self.experiment, tpoint_ix=batch['cycle'],
                    channel_ix=batch['channel'], zplane_ix=batch['zplane'],
                    illumcorr=batch['illumcorr'], shift=batch['shift'])

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
        '''
        Not implemented.
        '''
        raise AttributeError('"%s" object doesn\'t have a "collect_job_output"'
                             ' method' % self.__class__.__name__)

    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        '''
        Not implemented.
        '''
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
