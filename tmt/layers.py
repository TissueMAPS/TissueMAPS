import numpy as np
from shapely.geometry import box
from shapely.geometry.polygon import Polygon
import imageutil
import dafu
from illuminati import segment
from reader import ImageReader
from image import ChannelImage
from image import MaskImage


class Layer(object):

    '''
    Base class for a layer.

    A layer is a 2D grid of images (mosaic) that can be used to build a pyramid.
    '''

    def __init__(self, image_files, metadata):
        '''
        Initialize an instance of class Layer.

        Parameters
        ----------
        image_files: List[str]
            absolute paths to of the image files
        metadata: List[Dict[str, int or str]]
            metadata for each image in `image_files`
        '''
        self.image_files = image_files
        self.metadata = metadata
        self.mosaic = None

    @property
    def file_grid(self):
        '''
        Returns
        -------
        numpy.ndarray[str]
            image filenames arranged according to their position in the mosaic
        '''
        if self._file_grid is None:
            coordinates = [m.coordinates for m in self.metadata]
            height, width = np.max(coordinates, axis=0)
            self._file_grid = np.empty((height, width))
            for i, c in enumerate(coordinates):
                self._file_grid[c[0], c[1]] = self.image_files[i]
        return self._file_grid

    def stitch_mosaic(self, dx=0, dy=0):
        '''
        Load individual images and stitch them together according to the grid
        layout. To account for an overlap of images, the parameters
        `dx` and `dy` can be set.

        Parameters
        ----------
        dx: int, optional
            displacement in x direction
        dy: int, optional
            displacement in y direction

        Returns
        -------
        Vips.Image
            mosaic image
        '''
        with ImageReader('vips') as reader:
            rows = list()
            for i in xrange(self.file_grid.shape[0]):
                images_in_row = list()
                for j in xrange(self.file_grid.shape[1]):
                    images_in_row.append(reader.read(self.file_grid[i, j]))
                rows.append(reduce(lambda x, y: x.merge(y, 'horizontal',
                                   dx, 0), images_in_row))
        self.mosaic = reduce(lambda x, y: x.merge(y, 'vertical', 0, dy),
                             rows)
        return self.mosaic

    def align(self, shift_descriptions):
        '''
        Align mosaic according to pre-calculated shift values.

        To this end, the information stored in shift descriptor files is used.
        These files contain the shift between each pair of images from the
        obj_meta and the reference cycle in x and y direction. For the global
        alignment we use the median of the individual shift values. Based on
        those values, the intersection of mosaic images from different cycles
        is computed and the respective area is extracted form each image.

        .. Warning::

            The mosaic image might have different dimensions after alignment.

        Parameters
        ----------
        shift_descriptions: List[ShiftDescription]
            shift description for each cycle

        Returns
        -------
        Vips.Image
            aligned mosaic image

        Raises
        ------
        AttributeError
            when mosaic does not exist
        '''
        if self.mosaic is None:
            raise AttributeError('Mosaic does not exist. '
                                 'Call "stitch_mosaic" method first.')
        cycle_nrs = [d[0].cycle for d in shift_descriptions]
        current_cycle_ix = cycle_nrs.index(self.metadata[0].cycle)

        # TODO: global shifts could already be stored upon shift calculation!
        x_shifts = list()
        y_shifts = list()
        for d in shift_descriptions:
            x_shifts.append(np.median([s.x_shift for s in d]))
            y_shifts.append(np.median([s.y_shift for s in d]))

        # Create a Shapely rectangle for each image
        boxes = [box(x, y, x + self.mosaic.width, y + self.mosaic.height)
                 for x, y in zip(x_shifts, y_shifts)]

        # Compute the intersection of all those rectangles
        intersection = reduce(Polygon.intersection, boxes)
        min_x, min_y, max_x, max_y = intersection.bounds

        # How much to cut from the left side and from the top
        this_box = boxes[current_cycle_ix].bounds
        offset_left = min_x - this_box[0]
        offset_top = min_y - this_box[1]

        # How large is the extracted area (dimensions of the intersection)
        intersection_width = max_x - min_x
        intersection_height = max_y - min_y

        self.mosaic_image = self.mosaic_image.extract_area(
            offset_left, offset_top, intersection_width, intersection_height)

        return self.mosaic_image

    def scale(self):
        '''
        Scale mosaic image.

        Searches the image for the maximum and minimum value,
        then returns the image as unsigned 8-bit, scaled such that the maximum
        value is 255 and the minimum is zero.

        Returns
        -------
        Vips.Image
            scaled mosaic

        Raises
        ------
        AttributeError
            when mosaic does not exist
        '''
        if self.mosaic is None:
            raise AttributeError('Mosaic does not exist. '
                                 'Call "stitch_mosaic" method first.')
        self.mosaic = self.mosaic.scale()
        return self.mosaic

    def save(self, output_filename, quality):
        '''
        Write mosaic to file as JPEG.

        Parameters
        ----------
        output_filaname: str
            full path to the location were the image should be saved
        quality: int
            quality of the JPEG image (defaults to 75)
        '''
        if self.mosaic is None:
            raise AttributeError('Mosaic has not yet been created. '
                                 'Call "stitch_mosaic" method first.')
        imageutil.save_vips_image_jpg(self.mosaic, output_filename, quality)

    def create_pyramid(self, pyramid_dir):
        '''
        Create zoomify pyramid (8-bit grayscale JPEG images).

        Parameters
        ----------
        pyramide_dir: str
            path to the folder where pyramid should be saved

        Raises
        ------
        AttributeError
            when mosaic does not exist
        '''
        if self.mosaic is None:
            raise AttributeError('Mosaic does not exist. '
                                 'Call "stitch_mosaic" method first.')
        self.mosaic_image.dzsave(pyramid_dir, layout='zoomify',
                                 suffix='.jpg[Q=100]')


class ChannelLayer(Layer):

    '''
    Class for a channel layer, i.e. a mosaic layer that can be displayed
    in TissueMAPS as a single grayscale channel or combined with other channels
    to RGB (additive color blending).
    '''

    def __init__(self, image_files, metadata):
        '''
        Initialize an instance of class Layer.

        Parameters
        ----------
        image_files: List[str]
            absolute paths to of the image files
        metadata: List[Dict[str, int or str]]
            metadata for each image in `image_files`
        '''
        Layer.__init__(self, image_files, metadata)
        self.image_files = image_files
        self.metadata = metadata

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the layer (will become the name of the pyramid directory)
        '''
        self._name = self.metadata[0].channel
        return self._name

    def stitch_mosaic(self, stats=None, dx=0, dy=0):
        '''
        Load individual images and stitch them together according to the grid
        layout. To account for an overlap of images, the parameters
        `dx` and `dy` can be set.

        Channel layers are used in TissueMAPS to display the actual
        fluorescence microscopy images. These may exhibit illumination
        artifacts that should be corrected before display.
        To this end, illumination statistics can be provided, which are used
        to correct individual images before they are stitched together.

        Parameters
        ----------
        stats: List[Vips.Image], optional
            illumination statistics (mean and standard deviation images);
            when provided they are automatically applied
        dx: int, optional
            displacement in x direction
        dy: int, optional
            displacement in y direction

        Returns
        -------
        Vips.Image
            mosaic image

        See also
        --------
        `corilla`_
        `illumstats`_
        '''
        with ImageReader('vips') as reader:
            rows = list()
            for i in xrange(self.file_grid.shape[0]):
                images_in_row = list()
                for j in xrange(self.file_grid.shape[1]):
                    im = ChannelImage(reader.read(self.file_grid[i, j]))
                    if stats:
                        im = im.correct(stats[0], stats[1])
                    images_in_row.append(im)
                rows.append(reduce(lambda x, y: x.merge(y, 'horizontal',
                                   dx, 0), images_in_row))
        self.mosaic = reduce(lambda x, y: x.merge(y, 'vertical', 0, dy),
                             rows)
        return self.mosaic

    def clip(self, thresh_value=None, thresh_percent=None):
        '''
        Clip (limit) the pixel values in the mosaic image.

        Given a threshold level, values above threshold are set
        to the threshold level.

        Parameters
        ----------
        thresh_value: int
            pixel value
        thresh_percent: int
            threshold above which there are `thresh_percent` pixel values

        Returns
        -------
        Vips.Image
            clipped mosaic

        Raises
        ------
        AttributeError
            when mosaic does not exist
        '''
        if self.mosaic is None:
            raise AttributeError('Mosaic does not exist. '
                                 'Call "stitch_mosaic" method first.')
        if not thresh_value:
            thresh_value = self.mosaic.percent(thresh_percent)
        condition_image = self.mosaic > thresh_value
        self.mosaic = condition_image.ifthenelse(thresh_value, self.mosaic)
        return self.mosaic


class MaskLayer(Layer):

    '''
    Class for a mask layer, i.e. a mosaic layer that can be displayed
    in TissueMAPS as a mask (overlay ontop of grayscale or RGB).
    '''

    def __init__(self, image_files, metadata, data_file):
        '''
        Initialize an instance of class Layer.

        Parameters
        ----------
        image_files: List[str]
            absolute paths to of the image files
        metadata: List[Dict[str, int or str]]
            metadata for each image in `image_files`
        data_file: str
            absolute path to the data file (HDF5 file that holds measurement
            data for each object in the images in `image_files`)
        '''
        Layer.__init__(self, image_files, metadata)
        self.image_files = image_files
        self.metadata = metadata
        self.data_file

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the layer (will become the name of the pyramid directory)
        '''
        self._name = self.metadata[0].objects
        return self._name

    def stitch_mosaic(self, outlines=True, dx=0, dy=0):
        '''
        Load individual images and stitch them together according to the grid
        layout. To account for an overlap of images, the parameters
        `dx` and `dy` can be set.

        Mask layers are used in TissueMAPS to visualize the position of
        segmented objects. In addition, these objects can be selected
        (i.e. one can click on them) and use the corresponding measured
        features for further analysis. There may be objects in the images,
        that we don't want to display, either because there are no data points
        for them available in the dataset (for example due to alignment)
        or because they lie at the border of individual images, which
        would result in incomplete and biased measurements for these objects.
        Therefore, we remove these objects from the images before stitching,
        i.e. we set the corresponding pixel values to zero.

        To this end, certain measurements are required for the objects, such
        as their ids and their hierarchical relation to other types of objects,
        and these measurements are retrieved from a pre-generated dataset
        (stored in HDF5 format).

        Note that removal of objects is based on the parent objects (e.g. cells)
        and that all children objects (e.g. nuclei) are removed, too.

        Parameters
        ----------
        outlines: bool, optional
            whether only the outlines of objects should be kept
            (defaults to ``True``)
        dx: int, optional
            displacement in x direction
        dy: int, optional
            displacement in y direction

        Returns
        -------
        Vips.Image
            mosaic image

        See also
        --------
        `dafu`_
        '''
        obj_name = self.metadata[0].objects.lower()
        # Get ids for current objects from dataset (pandas data frames)
        obj, parent = dafu.utils.extract_ids(self.data_file, obj_name)
        with ImageReader('vips') as reader:
            rows = list()
            for i in xrange(self.file_grid.shape[0]):
                images_in_row = list()
                for j in xrange(self.file_grid.shape[1]):
                    im = MaskImage(reader.read(self.file_grid[i, j]))
                    # Objects without data points
                    current_metadata = [m for m in self.metadata
                                        if m.filename == self.file_grid[i, j]]
                    site = current_metadata.site
                    ids_image = obj.ids
                    ids_data = np.unique(obj['ID_parent'][obj.ID_site == site])
                    ids_nodata = [o for o in ids_data if o not in ids_image]
                    # Border objects
                    ids_border = parent['ID_object'][(parent.IX_border > 0) &
                                                     (parent.ID_site == site)]
                    ids_border = ids_border.tolist()
                    ids_remove = ids_border + ids_nodata
                    im = segment.remove_objects_vips(im, ids_remove)
                    if outlines:
                        im = segment.outlines_vips(im)
                    images_in_row.append(im)
                rows.append(reduce(lambda x, y: x.merge(y, 'horizontal',
                            dx, 0), images_in_row))
        self.mosaic = reduce(lambda x, y: x.merge(y, 'vertical', 0, dy), rows)
        return self.mosaic


class BrightfieldLayer(Layer):

    '''
    Class for a brightfield layer, i.e. a mosaic layer that can be displayed
    in TissueMAPS as RGB.
    '''

    def __init__(self, image_files, metadata):
        self.image_files = image_files
        self.metadata = metadata

    # TODO: preprocessing step: use openslide to extract image at highest
    # resolution from provided pyramid and save individual images (cut).
    # then business as usual


class LabelLayer(Layer):

    '''
    Class for a label layer, i.e. a labeled mask layer that encodes the
    global unique ids of objects (connected components). It is used in
    TissueMAPS to map pixel positions to objects ids.
    '''

    def __init__(self, image_files, metadata):
        Layer.__init__(self, image_files, metadata)
        self.image_files = image_files
        self.metadata = metadata

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the layer (will become the name of the pyramid directory)
        '''
        self._name = self.metadata[0].objects
        return self._name

    def stitch_mosaic(self, outlines=False, dx=0, dy=0):
        '''
        Load individual images and stitch them together according to the grid
        layout. To account for an overlap of images, the parameters
        `dx` and `dy` can be set.

        Label layers are used in TissueMAPS to visualize measured features or
        analysis results on the segmented objects by dynamically colorizing
        them according the calculated values.
        To this end, the pixels belonging to each object must be identifiable
        by a unique value. This global id is encoded by three digits,
        which allows 3^(2^16) different objects to be encoded in a 16-bit RGB
        image.

        Parameters
        ----------
        outlines: bool, optional
            whether only the outlines of objects should be kept
            (defaults to ``False``)
        dx: int, optional
            displacement in x direction
        dy: int, optional
            displacement in y direction

        Returns
        -------
        Vips.Image
            mosaic image

        See also
        --------
        `illuminati.segment.local_to_global_ids_vips`_
        '''
        max_id = 0
        with ImageReader('vips') as reader:
            rows = list()
            for i in xrange(self.file_grid.shape[0]):
                images_in_row = list()
                for j in xrange(self.file_grid.shape[1]):
                    im = MaskImage(reader.read(self.file_grid[i, j]))
                    im, max_id = segment.local_to_global_ids_vips(im, max_id)
                    max_id += 1
                    if outlines:
                        im = segment.outlines_vips(im)
                    images_in_row.append(im)
                rows.append(reduce(lambda x, y: x.merge(y, 'horizontal',
                            dx, 0), images_in_row))
        self.mosaic = reduce(lambda x, y: x.merge(y, 'vertical', 0, dy), rows)
        return self.mosaic

    def create_pyramid(self, pyramid_dir):
        '''
        Create zoomify pyramid (16-bit RGB PNG images).

        Parameters
        ----------
        pyramide_dir: str
            path to the folder where pyramid should be saved
        '''
        self.mosaic_image.dzsave(pyramid_dir, layout='zoomify', suffix='.png')

    def scale(self):
        '''
        Raises
        ------
        AttributeError
            label layers should not be rescaled to 8-bit
        '''
        raise AttributeError('"LabelLayers" object has no method "scale"')
