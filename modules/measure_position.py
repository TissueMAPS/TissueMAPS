from skimage import measure, morphology
import numpy as np
import jtapi
from tmlib.imageutil import find_border_objects


def measure_position(objects_image, objects_name, outlines, **kwargs):
    '''
    Jterator module for measuring the position of objects
    (connected components) in a label image.

    The module saves the row and column coordinates of the centroid
    ("Centroid_y" and "Centroid_y") the outline ("Outline_y" and "Outline_x")
    of each object as well as the index of objects at the border of the
    image ("BorderIx").

    Parameters
    ----------
    objects_image: numpy.ndarray[int]
        input label image
    objects_name: str
        name of the objects (labeled connected components) in `objects_image`
    outlines: bool
        whether coordinates of object outlines should be saved
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"
    '''
    data = dict()

    # Get coordinates of region containing individual objects
    regions = measure.regionprops(objects_image)
    centroids = np.array([r.centroid for r in regions])
    data['%s_Centroid_y' % objects_name] = centroids[:, 0]  # row
    data['%s_Centroid_x' % objects_name] = centroids[:, 1]  # column

    if outlines:
        # Get coordinates of pixels at the perimeter of objects:
        # First erode objects and then determine their contour
        eroded_image = morphology.binary_erosion(objects_image > 0)
        contours = measure.find_contours(eroded_image, False)
        for i in xrange(len(contours)):
            data['%s_Outline_y' % objects_name] = contours[i, 0]  # row
            data['%s_Outline_x' % objects_name] = contours[i, 1]  # column

    # Get indices of objects at the border of the image
    data['%s_BorderIx' % objects_name] = find_border_objects(objects_image)

    jtapi.writedata(data, kwargs['data_file'])
