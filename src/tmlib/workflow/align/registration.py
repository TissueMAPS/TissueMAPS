import os
import numpy as np
import logging
import image_registration
from ..readers import DatasetReader
from ..writers import DatasetWriter
from ..readers import ImageReader

logger = logging.getLogger(__name__)


def calculate_shift(target_image, reference_image):
    '''
    Calculate displacement between two images based on fast Fourier transform.

    Parameters
    ----------
    target_image: numpy.ndarray
        image that should be registered
    reference_image: numpy.ndarray
        image that should be used as a reference

    Returns
    -------
    Tuple[int]
        shift in x, y direction
    '''
    x, y, a, b = image_registration.chi2_shift(target_image, reference_image)
    return (x, y)


def register_images(sites, target_files, reference_files, output_file):
    '''
    Calculate shift between a set of two images (image to register and
    reference image) from two different acquisition cycles
    and store the results in an HDF5 file.

    Parameters
    ----------
    sites: List[int]
        acquisition sites (numbers in the acquisition sequence)
    target_files: List[Dict[str, List[str]]]
        path to the image files from the cycles that should be registered
    reference_files: List[str]
        path to the image files from the cycle that is used as reference for
        registration
    output_file: str
        path to the HDF5 file, where calculated values will be stored
    '''
    out = dict()
    for cycle, files in target_files.iteritems():
        logger.info('register images of cycle "%s"' % cycle)
        out[cycle] = dict()
        out[cycle]['x_shift'] = list()
        out[cycle]['y_shift'] = list()
        out[cycle]['filename'] = list()
        out[cycle]['site'] = list()
        for i in xrange(len(files)):
            target_filename = files[i]
            logger.info('target:    %s'
                        % os.path.basename(target_filename))
            ref_filename = reference_files[i]
            logger.info('reference: %s'
                        % os.path.basename(ref_filename))

            # Calculate shift between images
            with ImageReader() as reader:
                target_image = reader.read(target_filename)
                reference_image = reader.read(ref_filename)
            x, y = calculate_shift(target_image, reference_image)

            # Store shift values and name of the registered image
            out[cycle]['x_shift'].append(int(x))
            out[cycle]['y_shift'].append(int(y))
            out[cycle]['filename'].append(os.path.basename(target_filename))
            out[cycle]['site'].append(sites[i])

    logger.debug('write registration to file: %s' % output_file)
    with DatasetWriter(output_file, truncate=True) as writer:
        for cycle, data in out.iteritems():
            for feature, values in data.iteritems():
                # The calculated features will be stored
                # in separate datasets grouped by cycle
                hdf5_location = '%s/%s' % (cycle, feature)
                writer.write(hdf5_location, data=values)


def calculate_local_overhang(x_shift, y_shift):
    '''
    Calculates the overhang of images at one acquisition site
    across different acquisition cycles.

    Parameters
    ----------
    x_shift: List[int]
        shift values in x direction
    y_shift: List[int]
        shift values in y direction

    Returns
    -------
    List[int]
        upper, lower, right and left overhang
    '''
    # in y direction
    y_positive = [i > 0 for i in y_shift]
    y_negetive = [i < 0 for i in y_shift]
    if any(y_positive):  # down
        bottom = []
        for i in y_positive:
            bottom.append(y_shift[i])
        bottom = max(bottom)
    else:
        bottom = 0

    if any(y_negetive):  # up
        top = []
        for i in y_negetive:
            top.append(y_shift[i])
        top = abs(min(top))
    else:
        top = 0

    # in x direction
    x_positive = [i > 0 for i in x_shift]
    x_negetive = [i < 0 for i in x_shift]
    if any(x_positive):  # right
        right = []
        for i in x_positive:
            right.append(x_shift[i])
        right = max(right)
    else:
        right = 0

    if any(x_negetive):  # left
        left = []
        for i in x_negetive:
            left.append(x_shift[i])
        left = abs(min(left))
    else:
        left = 0

    return (top, bottom, right, left)


def fuse_registration(output_files, cycle_names):
    '''
    For each acquisition cycle, fuse calculated shifts stored across
    several HDF5 files.

    Parameters
    ----------
    output_files: List[str]
        names of HDF5 files, where registration results were stored
    cycle_names: List[str]
        names of cycles (correspond to groups in HDF5 files)

    Returns
    -------
    List[List[Dict[str, str or int]]]
        "x_shift", "y_shift", "filename", "site" and "cycle" of each
        registered image and each cycle
    '''
    shift_descriptor = [list() for name in cycle_names]
    for f in output_files:
        for i, key in enumerate(cycle_names):
            with DatasetReader(f) as reader:
                filenames = reader.read(os.path.join(key, 'filename'))
                x_shifts = reader.read(os.path.join(key, 'x_shift'))
                y_shifts = reader.read(os.path.join(key, 'y_shift'))
                sites = reader.read(os.path.join(key, 'site'))
                for j in xrange(len(filenames)):
                    shift_descriptor[i].append({
                        'filename': filenames[j],
                        'x_shift': x_shifts[j],
                        'y_shift': y_shifts[j],
                        'site': sites[j],
                        'cycle': key
                    })
    return shift_descriptor


def calculate_overhang(shift_descriptor, max_shift):
    '''
    Calculate the maximum overhang of images across all sites and
    across all acquisition cycles. The images will later be cropped according
    to this overhang. In order to limit the extent of cropping, `max_shift` can
    be set.

    Parameters
    ----------
    shift_descriptor: List[List[Dict[str, str or int]]]
        calculated shift values (and names) of registered images for
        each acquisition cycle
    max_shift: int
        maximally tolerated shift (in pixels)

    Returns
    -------
    Tuple[List[int or bool]]
        upper, lower, right, and left overhang per site (in pixels)
        and boolean indices of sites were shift exceeds maximally tolerated
        value (``True`` if no shift should be performed for that site)
    '''
    top_ol = list()
    bottom_ol = list()
    right_ol = list()
    left_ol = list()
    no_shift = list()
    number_of_sites = len(shift_descriptor[0])
    for site in xrange(number_of_sites):
        x_shift = np.array([c[site]['x_shift'] for c in shift_descriptor])
        y_shift = np.array([c[site]['y_shift'] for c in shift_descriptor])
        no_shift.append(any(abs(x_shift) > max_shift) or
                        any(abs(y_shift) > max_shift))
        top, bottom, right, left = calculate_local_overhang(x_shift, y_shift)
        top_ol.append(top)
        bottom_ol.append(bottom)
        right_ol.append(right)
        left_ol.append(left)

    # Calculate total overhang across all sites
    top_ol = int(max(map(abs, top_ol)))
    bottom_ol = int(max(map(abs, bottom_ol)))
    right_ol = int(max(map(abs, right_ol)))
    left_ol = int(max(map(abs, left_ol)))

    # Limit total overhang by maximally tolerated shift
    if top_ol > max_shift:
        top_ol = max_shift
    if bottom_ol > max_shift:
        bottom_ol = max_shift
    if right_ol > max_shift:
        right_ol = max_shift
    if left_ol > max_shift:
        left_ol = max_shift

    return (top_ol, bottom_ol, right_ol, left_ol, no_shift)
