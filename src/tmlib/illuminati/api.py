import os
import logging
import numpy as np
from ..layer import ChannelLayer
from ..readers import DatasetReader
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
        # TODO: if a clip percentile is provided instead of a clip value
        # a pre-calculated value should be retrieved from the illumination
        # correction file
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
                            'pyramid_dirs': [
                                os.path.join(
                                    self.experiment.layers_dir, name)
                            ]
                        },
                        'cycle': cycle.index,
                        'channel': channel,
                        'zplane': zplane,
                        'align': args.align,
                        'illumcorr': args.illumcorr,
                        'clip': args.clip,
                        'clip_value': args.clip_value
                    })
        return job_descriptions

    def run_job(self, batch):
        '''
        Create 8-bit greyscale JPEG zoomify pyramid layer of "channel" images.

        Parameters
        ----------
        batch: dict
            job_descriptions element

        See also
        --------
        :py:class:`tmlib.illuminati.layers.ChannelLayer`
        '''
        t = batch['cycle']
        c = batch['channel']
        z = batch['zplane']
        logger.info('create pyramid for layer "%s": '
                    'time point %d, channel %d, z-plane %d',
                    self.name, t, c, z)
        layer = ChannelLayer(
                    self.experiment, tpoint_ix=t, channel_ix=c, zplane_ix=z)

        layer.create_tile_groups()
        layer.create_image_properties_file()

        if batch['clip_value'] is None:
            logger.info('use default clip value')
            # Retrieve pre-calculated value from illumination statistics file
            cycle = self.experiment.plates[0].cycles[t]
            filename = cycle.illumstats_files[c]
            f = os.path.join(cycle.stats_dir, filename)
            with DatasetReader(f) as data:
                clip_value = data.read('/stats/percentile')
        else:
            clip_value = batch['clip_value']

        if batch['illumcorr']:
            logger.info('correct images for illumination artifacts')
        if batch['align']:
            logger.info('align images between cycles')

        # TODO: make use of `subset_indices` to parallelize the step
        layer.create_base_tiles(
                    clip_value=clip_value,
                    illumcorr=batch['illumcorr'], align=batch['align'])

        for level in reversed(range(len(layer.zoom_level_info)-1)):
            layer.create_downsampled_tiles(level)

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
