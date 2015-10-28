import re
import os
import logging
import pandas as pd
import bioformats
from natsort import natsorted
from collections import defaultdict
from cached_property import cached_property
from . import utils
from .readers import XmlReader
from .readers import JsonReader
from .image import is_image_file
from .image import ChannelImage
from .image import IllumstatsImages
from .metadata import ChannelImageMetadata
from .metadata import IllumstatsImageMetadata
from .errors import RegexError
from metaconfig import ome_xml
from align.descriptions import AlignmentDescription

logger = logging.getLogger(__name__)


class Cycle(object):
    '''
    A *cycle* represents an individual image acquisition time point
    as part of a time series experiment and corresponds to a folder on disk.

    The `Cycle` class provides attributes and methods for accessing the
    contents of this folder.

    See also
    --------
    :mod:`tmlib.experiment.Experiment`
    '''

    CYCLE_DIR_FORMAT = 'cycle_{index:0>2}'

    STATS_FILE_FORMAT = 'channel_{channel_ix}.stat.h5'

    def __init__(self, cycle_dir, user_cfg, library):
        '''
        Initialize an instance of class Cycle.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        user_cfg: Dict[str, str]
            additional user configuration settings
        library: str
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``)

        Returns
        -------
        tmlib.cycle.Cycle

        Raises
        ------
        OSError
            when `cycle_dir` does not exist

        See also
        --------
        :mod:`tmlib.cfg.UserConfiguration`
        '''
        self.cycle_dir = os.path.abspath(cycle_dir)
        if not os.path.exists(self.cycle_dir):
            raise OSError('Cycle directory does not exist.')
        self.user_cfg = user_cfg
        self.library = library

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the cycle folder
        '''
        return self.cycle_dir

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the cycle folder
        '''
        return os.path.basename(self.dir)

    @property
    def plate_name(self):
        '''
        Returns
        -------
        str
            name of the plate to which images of this cycle belong
        '''
        return os.path.basename(os.path.dirname(self.dir))

    @property
    def index(self):
        '''
        A *cycle* represents a time point in a time series. The `index`
        is the zero-based index of the *cycle* in this sequence.
        It is encoded in the name of the *cycle* folder and is retrieved from
        it using a regular expression.

        Returns
        -------
        int
            zero-based cycle index

        Raises
        ------
        RegexError
            when `index` cannot not be determined from folder name
        '''
        regexp = utils.regex_from_format_string(self.CYCLE_DIR_FORMAT)
        match = re.search(regexp, self.name)
        if not match:
            raise RegexError(
                    'Can\'t determine cycle id number from folder "%s" '
                    'using format "%s" provided by the configuration settings.'
                    % (self.name, self.CYCLE_DIR_FORMAT))
        return int(match.group('index'))

    @property
    def experiment_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the parent experiment directory
        '''
        return os.path.dirname(self.dir)

    @property
    def experiment(self):
        '''
        Returns
        -------
        str
            name of the corresponding parent experiment folder
        '''
        return os.path.basename(os.path.dirname(self.dir))

    @cached_property
    def image_dir(self):
        '''
        Returns
        -------
        str
            path to the folder holding the image files

        Note
        ----
        The directory is created if it doesn't exist.
        '''
        image_dir = os.path.join(self.dir, 'images')
        if not os.path.exists(image_dir):
            logger.debug('create directory for image files: %s', image_dir)
            os.mkdir(image_dir)
        return image_dir

    @property
    def image_files(self):
        '''
        Returns
        -------
        List[str]
            names of files in `image_dir`

        Raises
        ------
        OSError
            when no image files are found in `image_dir`

        See also
        --------
        :mod:`tmlib.image.is_image_file`
        '''
        files = [
            f for f in os.listdir(self.image_dir) if is_image_file(f)
        ]
        files = natsorted(files)
        if not files:
            raise OSError('No image files found in "%s"' % self.image_dir)
        return files

    @property
    def image_metadata_file(self):
        '''
        Returns
        -------
        str
            name of the OMEXML file containing cycle-specific image metadata
        '''
        return 'image_metadata.ome.xml'

    @property
    def align_descriptor_file(self):
        '''
        Returns
        -------
        str
            name of the file that contains cycle-specific descriptions required
            for the alignment of images of the current cycle relative to the
            reference cycle
        '''
        return 'alignment_description.json'

    @cached_property
    def image_metadata_table(self):
        '''
        Returns
        -------
        pandas.DataFrame
            metadata for each file in `image_dir` in tabular form, where
            rows represent images and columns hold the values for different
            metadata attributes

        Raises
        ------
        OSError
            when metadata file does not exist

        Note
        ----
        The table representation of metadata is cached in memory and allows
        efficient indexing. See
        `pandas docs <http://pandas.pydata.org/pandas-docs/stable/indexing.html>`_
        for details on indexing and selecting data.
        '''
        metadata_file = os.path.join(self.dir, self.image_metadata_file)
        with XmlReader() as reader:
            metadata = bioformats.OMEXML(reader.read(metadata_file))
        # Bring metadata into the following format: List[dict], which makes
        # it easy to convert it into a pandas.DataFrame
        formatted_metadata = list()
        site_mapper = defaultdict(list)
        count = 0
        plt = metadata.plates[0]
        for w in plt.Well:
            for s in plt.Well[w].Sample:
                ref_id = s.ImageRef
                ref_ix = ome_xml.get_image_ix(ref_id)
                ref_im = metadata.image(ref_ix)
                formatted_metadata.append({
                    'name': ref_im.Name,
                    'plate_name': self.plate_name,
                    'well_name': w,
                    'well_pos_y': s.PositionY,
                    'well_pos_x': s.PositionX,
                    'channel_ix': ref_im.Pixels.Plane(0).TheC,
                    'channel_name': ref_im.Pixels.Channel(0).Name,
                    'zplane_ix': ref_im.Pixels.Plane(0).TheZ,
                    'tpoint_ix': ref_im.Pixels.Plane(0).TheT
                })
                # Collect list indices per unique acquisition site
                site_mapper[(w, s.PositionY, s.PositionX)].append(count)
                count += 1
        # Add the acquisition site index "site_ix" to each image element 
        sites = range(len(site_mapper))
        for i, indices in enumerate(site_mapper.values()):
            for ix in indices:
                formatted_metadata[ix]['site_ix'] = sites[i]
        # Add the alignment description to each image element (if available)
        alignment_file = os.path.join(self.dir, self.align_descriptor_file)
        if os.path.exists(alignment_file):
            with JsonReader() as reader:
                description = reader.read(alignment_file)
            align_description = AlignmentDescription(description)
            # Match shift descriptions via "site_ix"
            fmd_sites = [fmd['site_ix'] for fmd in formatted_metadata]
            align_sites = [shift.site_ix for shift in align_description.shifts]
            for i, s in enumerate(fmd_sites):
                overhang = align_description.overhang
                formatted_metadata[i]['upper_overhang'] = overhang.upper
                formatted_metadata[i]['lower_overhang'] = overhang.lower
                formatted_metadata[i]['right_overhang'] = overhang.right
                formatted_metadata[i]['left_overhang'] = overhang.left
                ix = align_sites.index(s)
                shift = align_description.shifts[ix]
                formatted_metadata[i]['x_shift'] = shift.x
                formatted_metadata[i]['y_shift'] = shift.y
        # Sort entries according to "name" to have the same order as the
        # values of attribute "image_files"
        metadata_table = pd.DataFrame(formatted_metadata).sort(['name'])
        metadata_table.index = range(len(metadata_table))
        return metadata_table

    @property
    def images(self):
        '''
        Returns
        -------
        List[tmlib.image.ChannelImage]
            image object for each image file in `image_dir`

        Note
        ----
        Image objects have lazy loading functionality, i.e. the actual image
        pixel array is only loaded into memory once the corresponding attribute
        (property) is accessed.

        Raises
        ------
        ValueError
            when names of image files and names in the image metadata are not
            the same
        '''
        images = list()
        filenames = self.image_metadata_table['name']
        if self.image_files != filenames.tolist():
            raise ValueError('Names of images do not match')
        for i, f in enumerate(self.image_files):
            image_metadata = ChannelImageMetadata()
            table = self.image_metadata_table[(filenames == f)]
            for attr in table:
                value = table.iloc[0][attr]
                setattr(image_metadata, attr, value)
            img = ChannelImage.create_from_file(
                    filename=os.path.join(self.image_dir, f),
                    metadata=image_metadata,
                    library=self.library)
            images.append(img)
        return images

    @cached_property
    def stats_dir(self):
        '''
        Returns
        -------
        str
            path to the directory holding illumination statistic files

        Note
        ----
        Directory is created if it doesn't exist.
        '''
        stats_dir = os.path.join(self.dir, 'stats')
        if not os.path.exists(stats_dir):
            logger.debug(
                'create directory for illumination statistics files: %s',
                stats_dir)
            os.mkdir(stats_dir)
        return stats_dir

    @cached_property
    def illumstats_files(self):
        '''
        Returns
        -------
        List[str]
            names of illumination correction files in `stats_dir`

        Raises
        ------
        OSError
            when `stats_dir` does not exist or when no illumination statistic
            files are found in `stats_dir`
        '''
        stats_pattern = self.STATS_FILE_FORMAT.format(channel_ix='\w+')
        stats_pattern = re.compile(stats_pattern)
        if not os.path.exists(self.stats_dir):
            raise OSError('Stats directory does not exist: %s'
                          % self.stats_dir)
        files = [
            f for f in os.listdir(self.stats_dir)
            if re.search(stats_pattern, f)
        ]
        files = natsorted(files)
        if not files:
            raise OSError('No illumination statistic files found in "%s"'
                          % self.stats_dir)
        illumstats_files = files
        return illumstats_files

    @property
    def illumstats_metadata(self):
        '''
        Returns
        -------
        List[tmlib.image.IllumstatsImageMetadata]
            metadata for each illumination statistic file in `stats_dir`

        Note
        ----
        Metadata information is retrieved from the filenames using regular
        expressions.

        Raises
        ------
        tmlib.errors.RegexError
            when required information could not be retrieved from filename
        '''
        illumstats_metadata = list()
        for f in self.illumstats_files:
            md = IllumstatsImageMetadata()
            regexp = utils.regex_from_format_string(self.STATS_FILE_FORMAT)
            match = re.search(regexp, f)
            if match:
                md.channel_ix = int(match.group('channel_ix'))
                md.tpoint_ix = self.index
                md.filename = f
            else:
                raise RegexError('Can\'t determine channel and cycle number '
                                  'from illumination statistic file "%s" '
                                  'using provided format "%s".\n'
                                  'Check your configuration settings!'
                                  % (f, self.STATS_FILE_FORMAT))
            illumstats_metadata.append(md)
        return illumstats_metadata

    @property
    def illumstats_images(self):
        '''
        Returns
        -------
        Dict[int, tmlib.image.IllumstatsImages]
            illumination statistics images for each channel

        Note
        ----
        Image objects have lazy loading functionality, i.e. the actual image
        pixel array is only loaded into memory once the corresponding attribute
        is accessed.
        '''
        illumstats_images = dict()
        for i, f in enumerate(self.illumstats_files):
            img = IllumstatsImages.create_from_file(
                    filename=os.path.join(self.stats_dir, f),
                    metadata=self.illumstats_metadata[i],
                    library=self.library)
            channel = self.illumstats_metadata[i].channel_ix
            illumstats_images[channel] = img
        return illumstats_images
