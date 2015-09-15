from shapely.geometry import box
from shapely.geometry.polygon import Polygon
import random
import copy
import os
import numpy as np
import itertools
import segment
import dafu
import tmt
from gi.repository import Vips
from tmt.illumstats import illum_correct_vips
from tmt import imageutil


class Mosaic(object):
    '''
    Class for a mosaic image, i.e. a large image stitched together
    from a grid of smaller images.

    Holds methods for image processing and pyramid creation.
    '''

    def __init__(self, images, cfg):
        '''
        Init class Mosaic.

        Parameters
        ----------
        images: List[tmt.image.Image]
            image objects with lazy loading method
        cfg: dict
            configuration settings
        '''
        self.images = images
        self.cfg = cfg
        self._image_grid = None
        self.mosaic_image = None
        self._mosaic_image_name = None

    @property
    def image_grid(self):
        '''
        Build a 2D list of image objects that specifies how the images
        should be stitched together. Each image object provides information
        the image (lazy loading) and additional meta information.

        Returns
        -------
        List[List[tmt.image.Image]]

        '''
        if self._image_grid is None:
            image_indices = [i.indices for i in self.images]
            height = max([c[0] for c in image_indices]) + 1
            width = max([c[1] for c in image_indices]) + 1
            grid = [[None for j in range(width)] for i in range(height)]
            for img, coord in zip(self.images, image_indices):
                i, j = coord
                grid[i][j] = img
            self._image_grid = grid
        return self._image_grid

    def _is_channel_layer(self):
        return isinstance(self.image_grid[0][0], tmt.image.ChannelImage)

    def _is_mask_layer(self):
        return isinstance(self.image_grid[0][0], tmt.image.SegmentationImage)

    def build_channel_grid(self):
        '''
        Build an image grid for channel images, i.e. load the actual intensity
        images into the image grid.

        Returns
        -------
        List[List[Vips.Image]]

        Raises
        ------
        AttributeError
            when channel grid is build from non-intensity images
        '''
        if not self._is_channel_layer():
            raise AttributeError('Channel grid can only be build from '
                                 'intensity images')
        self.layer_grid = copy.deepcopy(self.image_grid)
        for i in range(len(self.image_grid)):
            for j in range(len(self.image_grid[0])):

                im = self.image_grid[i][j].image

                self.layer_grid[i][j] = im

        return self.layer_grid

    def apply_illumination_correction_to_grid(self, stats):
        '''
        Apply illumination correction to each image in a grid of images.

        Parameters
        ----------
        stats: Tuple[Vips.Image[Vips.BandFormat.DOUBLE]]
            matrices with pre-calculated mean and standard deviation values

        Returns
        -------
        List[List[Vips.Image]]

        Raises
        ------
        TypeError
            when `stats` are not of correct type
        AttributeError
            when illumination correction is applied to non-intensity images
        '''
        if not self._is_channel_layer():
            raise AttributeError('Illumination correction can only be '
                                 'applied to intensity images')
        for i in range(len(self.layer_grid)):
            for j in range(len(self.layer_grid[0])):
                img = self.layer_grid[i][j]
                self.layer_grid[i][j] = illum_correct_vips(img,
                                                           stats.mean_image,
                                                           stats.std_image)
        return self.layer_grid

    def build_mask_grid(self, data_file, mask='outline',
                        global_ids=False):
        '''
        Build an image grid for mask images, i.e. load the actual segmentation
        images into the existing grid.

        Parameters
        ----------
        data_file: str
            Path to data.h5 HDF5 file holding the complete dataset.
        mask: str
            "outline" or "area"
        global_ids: bool
            Create a mask image that encodes the global object ids in RGB.

        Returns
        -------
        List[List[Vips.Image]]

        Raises
        ------
        AttributeError
            when mask grid is build from non-mask images
        '''
        if not self._is_channel_layer():
            raise AttributeError('Mask grid can only be build from '
                                 'intensity images')
        current_obj = self.image_grid[0][0].objects.lower()

        current, parent = dafu.util.extract_ids(data_file, current_obj)

        # Masks are used in TissueMAPS to visualize the position of
        # segmented objects in the image. In addition, they can be selected
        # (i.e. one can click on them) and use them with analysis tools.
        # Here we remove unwanted objects from the masks so that these objects
        # will not be displayed and cannot be selected.
        # Removal of objects is based on the parent objects (e.g. cells) and
        # all corresponding children objects (e.g. nuclei) will be removed, too
        # The internal hierarchical structure of the data file is hard-coded!
        # See dafu package for more info.

        self.layer_grid = copy.deepcopy(self.image_grid)

        max_id = 0
        for i in range(len(self.image_grid)):
            for j in range(len(self.image_grid[0])):

                im = self.image_grid[i][j].image

                # Which of the current objects are not in the dataset?
                # (Tracked via their parent object ids)
                site_id = self.image_grid[i][j].site
                ids_image = self.image_grid[i][j].ids
                ids_data = np.unique(current['ID_parent'][current.ID_site == site_id])
                ids_nodata = [o for o in ids_data if o not in ids_image]

                # Which parent objects lie at the border of the image?
                ids_border = parent['ID_object'][(parent.IX_border > 0) &
                                                 (parent.ID_site == site_id)]
                ids_border = ids_border.tolist()

                # Combine all object ids that should not be displayed and thus
                # removed from the images for the creation of masks
                ids_nodisplay = ids_border + ids_nodata

                # Should the ids be computed as RGB triples?
                # If yes, don't remove border cells and just create the RGB images!
                if global_ids:
                    # These masks will be used to visualize results of tools on 
                    # the objects. Keep all objects for these masks!
                    # Should the result be a RGB area mask or RGB outline mask
                    if mask == 'area':
                        im, max_id = segment.local_to_global_ids_vips(im, max_id)
                        max_id += 1
                    if mask == 'outline':
                        ids, max_id = segment.local_to_global_ids_vips(im, max_id)
                        max_id += 1
                        outline = segment.outlines_vips(im)
                        # Make everything except the outline black
                        im = outline.ifthenelse(ids, 0)
                else:
                    # These masks will be used for the display and selection of
                    # objects. Remove objects that should not be displayed
                    # (and will thus not be selectable).
                    if mask == 'area':
                        im = segment.remove_objects_vips(im, ids_nodisplay)
                    if mask == 'outline':
                        im = segment.remove_objects_vips(im, ids_nodisplay)
                        im = segment.outlines_vips(im)

                self.layer_grid[i][j] = im

        return self.layer_grid

    def stitch_images(self):
        '''
        Stitch all images according to the format given in the image grid.

        Returns
        -------
        Vips.Image

        Raises
        ------
        TypeError
            when images is not of correct type
        '''
        grid_height = len(self.layer_grid)
        row_images = []
        for i in range(grid_height):
            images_in_row = self.layer_grid[i]
            row_image = reduce(lambda x, y: x.join(y, 'horizontal'),
                               images_in_row)
            row_images.append(row_image)

        mosaic_image = reduce(lambda x, y: x.join(y, 'vertical'), row_images)

        if not isinstance(mosaic_image, Vips.Image):
            raise TypeError('Images must be of type "Vips.Image"')

        self.mosaic_image = mosaic_image
        return self.mosaic_image

    def shift_stitched_image(self, cycles, current_cycle):
        '''
        Shift the stitched mosaic image in such a way that
        all images from different channels and masks overlay each other.

        To this end, we use the shift descriptor files.
        These files contain the shift between each pair of images from the
        current and the reference cycle in x and y direction.
        Note that they assume an inverted y-axis!
        x-shift of "+2" means that the image is shifted 2 pixel to the right
        with regards to the corresponding image in the reference cycle.
        y-shift of "+3" would mean that the image is shifted 3 pixel downwards
        with respect to the reference.

        Parameters
        ----------
        cycles: List[tmt.experiment.Subexperiment]
            cycle objects holding shift information
        current_cycle: int
            index of the currently processed cycle (one-based)

        Returns
        -------
        Vips.Image
        '''
        shift_descriptors = [c.project.shift_file.description for c in cycles]
        cycle_nrs = [c.cycle for c in cycles]
        current_cycle_idx = cycle_nrs.index(current_cycle)

        x_shifts = [np.median(desc.xShift) for desc in shift_descriptors]
        y_shifts = [np.median(desc.yShift) for desc in shift_descriptors]

        width, height = self.mosaic_image.width, self.mosaic_image.height

        # Create a Shapely rectangle for each image
        boxes = [box(x, y, x + width, y + height)
                 for x, y in zip(x_shifts, y_shifts)]

        # Compute the intersection of all those rectangles
        intersection = reduce(Polygon.intersection, boxes)
        minx, miny, maxx, maxy = intersection.bounds

        # How much to cut from the left side and from the top
        this_box = boxes[current_cycle_idx].bounds
        offset_left = minx - this_box[0]
        offset_top = miny - this_box[1]

        # How large is the extracted area (dimensions of the intersection)
        intersection_width = maxx - minx
        intersection_height = maxy - miny

        self.mosaic_image = self.mosaic_image.extract_area(
            offset_left, offset_top, intersection_width, intersection_height)

        return self.mosaic_image

    def apply_threshold_to_stitched_image(self,
                                          thresh_value=None,
                                          thresh_sample=None,
                                          thresh_percent=None):
        '''
        Apply a threshold to a mosaic image.

        If the 'thresh' argument has not been set with a particular pixel
        value, then a certain percentage of pixels with the highest values
        will be thresholded, i.e. their value will be set to the threshold
        level. The `args.thresh_sample` is the number of images that are used
        to determine the threshold level below which `args.thresh_percent`
        pixel values lie.

        Parameters
        ----------
        thresh_value: int
        thresh_sample: int
        thresh_percent: int

        Returns
        -------
        Vips.Image

        Raises
        ------
        AttributeError
            when thresholding is applied to non-intensity images
        '''
        if not self._is_channel_layer():
            raise AttributeError('Illumination correction can only be '
                                 'applied to channel layer images')
        if thresh_value:
            val = thresh_value
        else:
            thresh_percent = 100 - thresh_percent
            # The images from which to sample threshold
            images = list(itertools.chain(*self.image_grid))  # linearize
            # Adjust sample size if set too large
            if thresh_sample > len(images):
                thresh_sample = len(images)
            sample_images = random.sample(images, thresh_sample)
            val = imageutil.calc_threshold_level(sample_images, thresh_percent)
        # Create lookup table
        lut = imageutil.create_thresholding_LUT(val)
        # Map image through lookup table
        self.mosaic_image = self.mosaic_image.maplut(lut)

        return self.mosaic_image

    def scale_stitched_image(self):
        '''
        Scale mosaic image s.t. the pixel values fill the whole range
        of possible values (16-bit: 0 to 2^16) and then converted to 8-bit.

        Returns
        -------
        Vips.Image
        '''
        self.mosaic_image = self.mosaic_image.scale()
        return self.mosaic_image

    def save_stitched_image(self, output_dir, quality):
        '''
        Write stitched image to file as JPEG.

        Parameters
        ----------
        output_dir: str
            folder location were image should be saved
        quality: int
            quality of the JPEG image (defaults to 75)
        '''
        filename = os.path.join(output_dir, self.mosaic_image_name)
        imageutil.save_vips_image_jpg(self.mosaic_image, filename, quality)

    @property
    def mosaic_image_name(self):
        '''
        Build name for the mosaic image based on metainformation stored in the
        Image object. Names will differ between SegmentationImage and ChannelImage
        objects, since they hold different information, such as objects name
        or channel number, respectively.

        Returns
        -------
        str

        Raises
        ------
        TypeError
            when image files are of unknown type
        '''
        if self._mosaic_image_name is None:
            im = self.images[0]
            if isinstance(im, tmt.image.SegmentationImage):
                f = '{experiment}_{cycle}_segmented{objects}.jpg'.format(
                                            experiment=im.experiment,
                                            cycle=im.cycle,
                                            objects=im.objects)

            elif isinstance(im, tmt.image.ChannelImage):
                f = '{experiment}_{cycle}_{filter}_C{channel:0>2}.jpg'.format(
                                            experiment=im.experiment,
                                            cycle=im.cycle,
                                            filter=im.filter,
                                            channel=im.channel)
            else:
                raise TypeError('Image files must be of class "SegmentationImage" '
                                'or "ChannelImage"')
            self._mosaic_image_name = f
        return self._mosaic_image_name

    def create_pyramid(self, pyramid_dir, tile_file_extension='.jpg[Q=100]'):
        '''
        Create pyramid on disk.

        By default, 8-bit JPEG pyramids are created.
        If one wants to create 16 bit pyramids the suffix has to be PNG,
        otherwise the 16-bit images will be automatically converted
        to 8-bit JPEGs.

        Parameters
        ----------
        pyramide_dir: str
            path to the folder where pyramid should be saved
        tile_file_extension: str
            image file format: ".png" or ".jpg" (default)
        '''
        self.mosaic_image.dzsave(
            pyramid_dir, layout='zoomify', suffix=tile_file_extension)
