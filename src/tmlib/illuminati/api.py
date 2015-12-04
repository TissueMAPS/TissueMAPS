import os
import logging
import shutil
import numpy as np
from ..layer import ChannelLayer
from ..api import ClusterRoutines

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
        '''
        super(PyramidBuilder, self).__init__(
                experiment, prog_name, verbosity)
        self.experiment = experiment
        self.prog_name = prog_name
        self.verbosity = verbosity

    def create_job_descriptions(self, args):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.illuminati.args.IlluminatiInitArgs
            program-specific arguments

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
                md = cycle.image_metadata
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
                    logger.debug('create description for job # %d', j+1)
                    image_files = md.loc[indices]['name']
                    channel = np.unique(md.loc[indices]['channel_ix'])[0]
                    zplane = np.unique(md.loc[indices]['zplane_ix'])[0]
                    layer_names = [
                        lmd.name
                        for lmd in self.experiment.layer_metadata.values()
                        if lmd.channel_ix == channel and
                        lmd.tpoint_ix == cycle.index and
                        lmd.zplane_ix == zplane
                    ]
                    if len(layer_names) != 1:
                        raise ValueError('Wrong number of layer names.')
                    name = layer_names[0]
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
                                    self.experiment.layers_dir, name)
                        },
                        'cycle': cycle.index,
                        'channel': channel,
                        'zplane': zplane,
                        'align': args.align,
                        'illumcorr': args.illumcorr,
                        'clip': args.clip,
                        'clip_value': args.clip_value,
                        'clip_percentile': args.clip_percentile
                    })
        return job_descriptions

    def run_job(self, batch):
        '''
        Create 8-bit greyscale JPEG zoomify pyramid layer of "channel" images.

        See also
        --------
        :py:class:`tmlib.illuminati.layers.ChannelLayer`
        '''
        logger.debug('create channel layer')
        layer = ChannelLayer.create(
                    experiment=self.experiment, tpoint_ix=batch['cycle'],
                    channel_ix=batch['channel'], zplane_ix=batch['zplane'],
                    illumcorr=batch['illumcorr'], align=batch['align'])

        if batch['clip']:
            logger.info('threshold intensities')
            layer = layer.clip(value=batch['clip_value'],
                               percentile=batch['clip_percentile'])

        layer = layer.scale()

        output_dir = batch['outputs']['pyramid_dir']
        if os.path.exists(output_dir):
            logger.info('remove existing image pyramid: %s', output_dir)
            # NOTE: this may cause problems on NFS
            shutil.rmtree(output_dir)

        logger.info('save image pyramid: %s', output_dir)
        layer.save(output_dir)

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
