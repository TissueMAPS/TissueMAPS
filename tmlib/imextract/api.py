import os
import numpy as np
import logging
from .. import image_utils
from .. import utils
from ..readers import BioformatsImageReader
from ..cluster import ClusterRoutines
from ..writers import ImageMetadataWriter

logger = logging.getLogger(__name__)


class ImageExtractor(ClusterRoutines):

    '''
    Class for extraction of pixel arrays (planes) stored in image files using
    the Bio-Formats library via
    `python-bioformats <https://github.com/CellProfiler/python-bioformats>`_.
    The extracted arrays are written to PNG files. This is done to save disk
    space due to (lossless) file compression and for downstream compatibility,
    since not many libraries are able to read images from the original file
    formats (often extended TIFF formats).
    '''

    def __init__(self, experiment, prog_name, verbosity):
        '''
        Initialize an instance of class ImageExtractor.

        Parameters
        ----------
        experiment: Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level
        '''
        super(ImageExtractor, self).__init__(experiment, prog_name, verbosity)
        self.experiment = experiment
        self.prog_name = prog_name
        self.verbosity = verbosity

    def _create_output_dirs(self):
        for cycle in self.cycles:
            if not os.path.exists(cycle.image_dir):
                os.mkdir(cycle.image_dir)

    def create_job_descriptions(self, **kwargs):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        **kwargs: dict
            additional input arguments as key-value pairs:
            * "batch_size": number of images per job (*int*)

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions

        Note
        ----
        There is some black magic happening behind the scenes:
        We want images from different cycles (time points) in separate
        folders, because they may be pre-processing independently.
        For example, illumination correction statistics are calculated
        for each cycle separately and cycles may have to be aligned
        relative to each other. In addition, the number of files that can
        (should be) stored in a directory is limited and we may end up having
        a lot of image files across the whole experiment.
        Each cycle can be uploaded separately, which is adequate when
        images were acquired and stored in separate files
        along with their corresponding metadata. However, often images
        of a time series acquisition are grouped together and in some
        cases are even all stored in a single file.
        If multiple time points are encountered in an upload folder, the
        mapping of upload folder to cycle is no longer 1 ->1 but 1 -> n,
        where n is the number of time points.
        A separate cycle folder is then created for each time point and
        the configured metadata for the corresponding images is dumped to
        this folder. The extracted images will subsequently also be written
        into the same cycle folder.
        '''
        joblist = dict()
        joblist['run'] = list()
        job_count = 0
        cycle_count = 0
        for upload in self.experiment.uploads:
            logger.debug('process images in upload directory "%s"'
                         % upload.dir)
            tpoints = [md.time_id for md in upload.image_metadata]
            unique_tpoints = sorted(set(tpoints))
            logger.debug('%d time points found' % len(unique_tpoints))
            hashmap = upload.image_hashmap
            lut = {
                i: k for k, v in hashmap.iteritems() for i in v['id']
            }
            # Create a cycle for each time point
            for t in unique_tpoints:
                logger.debug('process images belonging to time point %d' % t)
                try:
                    cycle = self.experiment.cycles[cycle_count]
                except IndexError:
                    cycle = self.experiment.append_cycle()
                index = utils.indices(tpoints, t)
                cycle_metadata = dict()
                logger.debug('update metadata attributes "time_id" and "name"')
                for i, md in enumerate(upload.image_metadata):
                    if i not in index:
                        continue
                    # Update time point identifiers
                    md.time_id = cycle.id
                    # Update the name of the image accordingly
                    fn = md.serialize()
                    fn.update({'experiment_name': self.experiment.name})
                    md.name = self.experiment.cfg.IMAGE_FILE.format(**fn)
                    ix = hashmap[lut[md.id]]['id'].index(md.id)
                    hashmap[lut[md.id]]['name'][ix] = md.name
                    cycle_metadata.update({md.name: md.serialize()})
                # Place the updated cycle metadata into the cycle folder
                with ImageMetadataWriter() as writer:
                    filename = os.path.join(cycle.dir,
                                            cycle.image_metadata_file)
                    writer.write(filename, cycle_metadata)

                # Take files that contain images belonging to the current cycle
                files = [lut[md['id']] for md in cycle_metadata.values()]
                img_batches = self._create_batches(files,
                                                   kwargs['batch_size'])
                md = self.experiment.cycles[0].image_metadata[0]
                for batch in img_batches:
                    job_count += 1
                    joblist['run'].append({
                        'id': job_count,
                        'inputs': {
                            'image_files': [
                                os.path.join(upload.image_dir, b)
                                for b in batch
                            ]
                        },
                        'outputs': {
                            'image_files': [
                                os.path.join(cycle.image_dir, name)
                                for b in batch
                                for name in hashmap[b]['name']
                            ]
                        },
                        'dimensions': md.orig_dimensions,
                        'dtype': md.orig_dtype,
                        'series': [
                            s for b in batch for s in hashmap[b]['series']
                        ],
                        'planes': [
                            p for b in batch for p in hashmap[b]['plane']
                        ],
                    })
                cycle_count += 1
        return joblist

    def run_job(self, batch):
        '''
        Extract individual planes from an image file and write each of them
        to a separate PNG file.

        Parameters
        ----------
        batch: dict
            joblist element, i.e. description of a single job
        '''
        with BioformatsImageReader() as reader:
            for i, filename in enumerate(batch['inputs']['image_files']):
                logger.info('extract images from file: %s'
                            % os.path.basename(filename))
                focal_planes = batch['planes'][i]
                stack = np.empty((len(focal_planes),
                                  batch['dimensions'][0],
                                  batch['dimensions'][1]),
                                 dtype=batch['dtype'])
                # If intensity projection should be performed there will
                # be multiple planes per output filename and the stack will
                # be multi-dimensional, i.e. stack.shape[0] > 1
                for z in xrange(len(focal_planes)):
                    stack[z, :, :] = reader.read_subset(
                                        filename,
                                        plane=z, series=batch['series'][i])
                img = np.max(stack, axis=0)
                # Write plane (2D single-channel image) to file
                output_filename = batch['outputs']['image_files'][i]
                logger.info('extracted image: %s'
                            % os.path.basename(output_filename))
                image_utils.save_image_png(img, output_filename)

    def collect_job_output(self, batch):
        raise AttributeError('"%s" object doesn\'t have a "collect_job_output"'
                             ' method' % self.__class__.__name__)

    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
