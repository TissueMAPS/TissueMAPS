from shapely.geometry import box
from shapely.geometry.polygon import Polygon
import random
import copy
import numpy as np
import itertools
import illumcorrect
import stitch
import segment
import datafusion.util
from tmt import imageutil


class Mosaic(object):
    '''
    A class for mosaic images for use with TissueMAPS.
    '''

    def __init__(self, images):
        '''
        Init class Mosaic.

        Parameters:
        -----------
        images: List[Image]
                Image objects with lazy loading method.
                Loaded images will be objects of class VIPSImage.
        '''
        self.images = images
        self._image_grid = None
        self.mosaic_image = None

    @property
    def image_grid(self):
        '''
        Build a 2D list of image objects that specifies how the images
        should be stitched together. Each image object provides information
        the image (lazy loading) and additional meta information.

        Returns:
        --------
        List[List[Image]]

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

    def build_channel_grid(self):
        '''
        Build an image grid for channel images, i.e. load the actual intensity
        images into the image grid.

        Returns:
        --------
        List[List[VIPSImage]]
        '''
        self.layer_grid = copy.deepcopy(self.image_grid)
        for i in range(len(self.image_grid)):
            for j in range(len(self.image_grid[0])):

                im = self.image_grid[i][j].image

                self.layer_grid[i][j] = im

        return self.layer_grid

    def apply_illumination_correction_to_grid(self, mean_image, std_image):
        '''
        Apply illumination correction to a grid image.

        Parameters:
        -----------
        mean_image: ndarray[float]
        std_image: ndarray[float]

        Returns:
        --------
        List[List[VIPSImage]]
        '''
        # TODO: only makes sense for channel images -> is_channel_layer()
        for i in range(len(self.layer_grid)):
            for j in range(len(self.layer_grid[0])):
                img = self.layer_grid[i][j]
                self.layer_grid[i][j] = \
                    illumcorrect.illum_correction_vips(img, mean_image, std_image)
        return self.layer_grid

    def build_mask_grid(self, data_file, mask='outline',
                        make_global_ids=False):
        '''
        Build an image grid for mask images, i.e. load the actual segmentation
        images into the existing grid.

        Parameters:
        -----------
        data_file: str
                   Path to data.h5 HDF5 file holding the complete dataset.
        mask: str
              "outline" or "area"
        make_global_ids: bool
                         Create a mask image that encodes the global object ids
                         in RGB.

        Returns:
        --------
        List[List[VIPSImage]]
        '''

        current_obj = self.image_grid[0][0].objects.lower()

        current, parent = datafusion.util.extract_ids(data_file, current_obj)

        # Masks are used in TissueMAPS to visualize the position of
        # segmented objects in the image. In addition, they can be selected
        # (i.e. one can click on them) and use them with analysis tools.
        # Here we remove unwanted objects from the masks so that these objects
        # will not be displayed and cannot be selected.
        # Removal of objects is based on the parent objects (e.g. cells) and
        # all corresponding children objects (e.g. nuclei) will be removed, too
        # The internal hierarchical structure of the data file is hard-coded!
        # See datafusion package for more info.

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
                if make_global_ids:
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

        Returns:
        --------
        VIPSImage
        '''
        grid_height = len(self.layer_grid)
        row_images = []
        for i in range(grid_height):
            images_in_row = self.layer_grid[i]
            row_image = reduce(lambda x, y: x.join(y, 'horizontal'),
                               images_in_row)
            row_images.append(row_image)

        self.mosaic_image = reduce(lambda x, y: x.join(y, 'vertical'),
                                   row_images)

        return self.mosaic_image

    def shift_stiched_image(self, cycles, current_cycle):
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

        Parameters:
        -----------
        cycles: List[Subexperiment]
                cycle objects holding shift information
        current_cycle: int
                       index of the currently processed cycle (one-based)

        Returns:
        --------
        VIPSImage
        '''
        shift_descriptors = [c.project.shift_file for c in cycles]
        cycle_nrs = [c.cycle for c in cycles]
        current_cycle_idx = cycle_nrs.index(current_cycle)

        x_shifts = [np.median(desc['xShift']) for desc in shift_descriptors]
        y_shifts = [np.median(desc['yShift']) for desc in shift_descriptors]

        width, height = self.mosaic_image.width, self.mosaic_image.height

        # Create a Shapely rectangle for each image
        boxes = [box(x, y, x + width, y + height)
                 for x, y in zip(x_shifts, y_shifts)]

        # Compute the intersection of all those rectangles
        this_box = boxes[current_cycle_idx].bounds
        intersection = reduce(Polygon.intersection, boxes)
        minx, miny, maxx, maxy = intersection.bounds

        # How much to cut from the left side and from the top
        offset_left = minx - this_box[0]
        offset_top = miny - this_box[1]

        # How large the area to extract is (= the dimensions of the intersection)
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
        to determine the threshold level above which the `args.thresh_percent`
        highest pixel values lie.

        Parameters:
        -----------
        thresh_value: int
        thresh_sample: int
        thresh_percent: int

        Returns:
        --------
        VipsImage
        '''
        # TODO: only makes sense for channel images -> check: is_channel_layer()
        if thresh_value:
            val = thresh_value
        else:
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

        Returns:
        --------
        VipsImage
        '''
        self.mosaic_image = self.mosaic_image.scale()
        return self.mosaic_image

    def create_pyramid(self, pyramid_dir, tile_file_extension='.jpg[Q=100]'):
        '''
        Create pyramid on disk.

        By default, 8-bit JPEG pyramids are created.
        If one wants to create 16 bit pyramids the suffix has to be PNG,
        otherwise the 16-bit images will be automatically converted
        to 8-bit JPEGs.

        Parameters:
        -----------
        pyramide_dir: str
                      Path to the folder where pyramid should be saved
        tile_file_extension: str
                             Image file format: ".png" or ".jpg" (default)
        '''
        self.mosaic_image.dzsave(
            pyramid_dir, layout='zoomify', suffix=tile_file_extension)
