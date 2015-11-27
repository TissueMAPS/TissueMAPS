import numpy as np
import mahotas as mh
from mahotas.features import surf
from scipy import ndimage as ndi
from skimage.filters import gabor_kernel
from jtlib import utils


GABOR_KERNELS = dict()
for theta in range(4):
    theta = theta / 4. * np.pi
    for sigma in (1, 3):
        for frequency in (0.05, 0.25):
            # Use the real parts of the Gabor filter kernel
            k = np.real(
                    gabor_kernel(
                        frequency, theta=theta, sigma_x=sigma, sigma_y=sigma))
            name = 'frequency%.2f-theta%.2f-sigma%d' % (frequency, theta, sigma)
            GABOR_KERNELS[name] = k


def build_dataset_name(objects_name, feature_name, subfeature_name,
                       layer_name=None):
    '''
    Build the name of a dataset based on the names of the images and the names
    of features that were measured in these images.

    Parameters
    ----------
    objects_name: str
        name of the objects for which measurements were obtained, e.g. "cells"
    feature_name: str
        name of the feature that was measured, e.g. "intensity"
    subfeature_name: str
        name of the subfeature or statistic that was measured, e.g. "mean"
    layer_name: str, optional
        name of the intensity image that was used for the measurements

    Returns
    -------
    str
        name of the dataset
    '''
    if layer_name:
        name = '{object}_{layer}_{feature}_{subfeature}'.format(
                        object=objects_name, layer=layer_name,
                        feature=feature_name,
                        subfeature=subfeature_name)
    else:
        name = '{object}_{feature}_{subfeature}'.format(
                        object=objects_name,
                        feature=feature_name,
                        subfeature=subfeature_name)
    return name


def measure_intensity(im, mask, region):
    '''
    Return intensity features from pre-calculated region properties.

    Parameters
    ----------
    im: numpy.ndarray[int]
        intensity image
    mask: numpy.ndarray[bool]
        mask image containing one object (i.e. one connected pixel component);
        must have the same size as `im`
    region: skimage.measure._regionprops._RegionProperties
        item of a region property list as returned by
        :py:func:`skimage.measure.regionprops`

    Raises
    ------
    ValueError
        when `im` and `mask` don't have the same size
    TypeError
        when elements of `mask` don't have type bool
    '''
    if not im.shape == mask.shape:
        raise ValueError('Images must have the same size.')
    if not mask.dtype == 'bool':
        raise TypeError('Mask image must have type bool.')
    im[mask == 0] = 0
    im_nan = im.astype(np.float)
    im_nan[im == 0] = np.nan  # replace zero values by NaN's
    feats = [
        region.max_intensity,
        region.mean_intensity,
        region.min_intensity,
        np.nansum(im_nan),  # ignore NaN
        np.nanstd(im_nan)  # ignore NaN
    ]
    names = [
        'max',
        'mean',
        'min',
        'sum',
        'std'
    ]
    names = ['Intensity_%s' % s for s in names]
    return dict(zip(names, feats))


def measure_area_shape(region):
    '''
    Return morphological features from pre-calculated region properties.

    Parameters
    ----------
    region: skimage.measure._regionprops._RegionProperties
        item of a region property list as returned by
        :py:func:`skimage.measure.regionprops`

    Returns:
        dictionary with names of the features as keys and the calculated values
    '''
    feats = [
        region.area,
        region.eccentricity,
        region.solidity,
        (4.0 * np.pi * region.area) / (region.perimeter**2)
    ]
    names = [
        'area',
        'eccentricity',
        'solidity',
        'form-factor'
    ]
    names = ['AreaShape_%s' % s for s in names]
    return dict(zip(names, feats))


def measure_hu(region):
    '''
    Return intensity-weighted Hu moments from pre-calculated region properties.

    Parameters:
        :region:        item of a region property list
                        (as returned by skimage.measure.regionprops)

    Returns:
        dictionary with names of the features as keys and the calculated values
    '''
    feats = region.weighted_moments_hu
    names = ['Hu_%d' % i for i in range(1, len(feats)+1)]
    return dict(zip(names, feats))


def measure_haralick(im, mask, bins=32):
    '''
    Calculate Haralick texture features.

    Parameters
    ----------
    im: numpy.ndarray[int]
        intensity image
    mask: numpy.ndarray[bool]
        mask image containing one object (i.e. one connected pixel component);
        must have the same size as `im`
    bins: int
        number of bins for downsampling of `im`

    Returns
    -------
    dict
        features

    Raises
    ------
    ValueError
        when `im` and `mask` don't have the same size
    TypeError
        when elements of `mask` don't have type bool
    '''
    if not im.shape == mask.shape:
        raise ValueError('Images must have the same size.')
    if not mask.dtype == 'bool':
        raise TypeError('Mask image must have type bool.')
    im[~mask] = 0
    # im_ds = utils.downsample_image(im, bins=bins)
    feats = mh.features.haralick(im, ignore_zeros=True, return_mean=True)
    names = [
        'angular-second-moment',
        'contrast',
        'correlation',
        'sum-of-squares',
        'inverse-diff-moment',
        'sum-avg',
        'sum-var',
        'sum-entropy',
        'entropy',
        'diff-var',
        'diff-entropy',
        'info-measure-corr-1',
        'info-measure-corr-2'
    ]
    names = ['Haralick_%s' % s for s in names]
    return dict(zip(names, feats))


def measure_tas(im, mask, threshold):
    '''
    Calculate Threshold Adjacency Statistics.

    Hamilton et al. 2007
    "Fast automated cell phenotype image classification"

    Parameters
    ----------
    im: numpy.ndarray[int]
        intensity image
    mask: numpy.ndarray[bool]
        mask image containing one object (i.e. one connected pixel component);
        must have the same size as `im`
    threshold: int
        threshold level

    Returns
    -------
    dict
        features

    Raises
    ------
    ValueError
        when `im` and `mask` don't have the same size
    TypeError
        when elements of `mask` don't have type bool
    '''
    if not im.shape == mask.shape:
        raise ValueError('Images must have the same size.')
    if not mask.dtype == 'bool':
        raise TypeError('Mask image must have type bool.')
    im[~mask] = 0
    feats = mh.features.pftas(im, T=threshold)
    names = ['center-%s' % i for i in xrange(9)] + \
            ['n-center-%s' % i for i in xrange(9)] + \
            ['mu-margin-%s' % i for i in xrange(9)] + \
            ['n-mu-margin-%s' % i for i in xrange(9)] + \
            ['mu-%s' % i for i in xrange(9)] + \
            ['n-mu-%s' % i for i in xrange(9)]
    names = ['TAS_%s' % s for s in names]
    return dict(zip(names, feats))


def measure_zernike(mask, radius=100):
    '''
    Calculate Zernike moments.

    Parameters
    ----------
    mask: numpy.ndarray[bool]
        mask image containing one object (i.e. one connected pixel component);
        must have the same size as `im`
    radius: int, optional
        scaling of `im` for normalization (default: ``100``) to account for the
        scale-invariance of Zernike moments

    Returns
    -------
    dict
        features

    Raises
    ------
    ValueError
        when `im` and `mask` don't have the same size
    TypeError
        when elements of `mask` don't have type bool
    '''
    if not mask.dtype == 'bool':
        raise TypeError('Mask image must have type bool.')
    degree = 12
    im_rs = mh.imresize(mask, [radius*2, radius*2])  # scaling invariant!
    feats = mh.features.zernike_moments(im_rs, degree=degree, radius=radius)
    names = []
    for n in xrange(degree+1):
        for l in xrange(n+1):
            if (n-l) % 2 == 0:
                names.append('%s-%s' % (n, l))
    names = ['Zernike_%s' % s for s in names]
    return dict(zip(names, feats))


def measure_gabor(im, mask):
    '''
    Calculate Gabor texture features.

    Parameters
    ----------
    im: numpy.ndarray[int]
        intensity image
    mask: numpy.ndarray[bool]
        mask image containing one object (i.e. one connected pixel component);
        must have the same size as `im`

    Returns
    -------
    dict
        features

    Raises
    ------
    ValueError
        when `im` and `mask` don't have the same size
    TypeError
        when elements of `mask` don't have type bool
    '''
    if not im.shape == mask.shape:
        raise ValueError('Images must have the same size.')
    if not mask.dtype == 'bool':
        raise TypeError('Mask image must have type bool.')
    feats = dict()
    for name, kernel in GABOR_KERNELS.iteritems():
        filtered = ndi.convolve(im.astype(float), kernel, mode='wrap')
        feats['Gabor_mean-%s' % name] = filtered[mask].mean()
        feats['Gabor_var-%s' % name] = filtered[mask].var()
        return feats


def measure_surf(im):
    '''
    Calculate Speeded-Up Robust Features (SURF).

    Coelho et al. 2013
    "Determining the subcellular location of new proteins from microscope
    images using local features"

    Parameters
    ----------
    im: numpy.ndarray[int]
        intensity image

    Returns
    -------
    dict
        features
    '''
    # im_i = surf.integral(im.copy())
    # points = surf.interest_points(im_i,
    #                               nr_octaves=6,
    #                               nr_scales=24,
    #                               max_points=1024,
    #                               is_integral=True)
    # feats = surf.descriptors(im_i,
    #                          interest_points=points,
    #                          is_integral=True,
    #                          descriptor_only=True)
    feats = surf.surf(im, nr_octaves=6, nr_scales=24, max_points=1024,
                      descriptor_only=True)
    # For some images no interest points are found. How do we handle these
    # features?
    print 'SURF features:'
    print feats
    names = ['SURF_%d' % i for i in range(1, len(feats)+1)]
    return dict(zip(names, feats))
