import numpy as np
import mahotas as mh
from mahotas.features import surf
from scipy import ndimage as ndi
from scipy.spatial import distance
from skimage.filters import gabor_kernel
from jtlib import utils


def get_gabor_kernels(theta_range=4, sigmas={1, 3}, frequencies={0.05, 0.25}):
    '''
    Build Gabor kernels for the calculation of texture features.

    Parameters
    ----------
    theta_range: int
        number of `theta` values
    sigmas: Set[int]
        values for `sigma_x` and `sigma_y`
    frequencies: Set[float]
        values for `frequency`

    Returns
    -------
    Dict[str, numpy.ndarray]
        real parts of the Garbor kernel for each combination of theta, sigma
        and frequency values

    Raises
    ------
    TypeError
        when arguments have wrong type

    See also
    --------
    :py:func:`skimage.filters.gabor_kernel`
    '''
    if not isinstance(theta_range, int):
        raise TypeError('Argument "theta_range" must have type int.')
    if not isinstance(sigmas, set):
        raise TypeError('Argument "sigmas" must have type set.')
    if not all([isinstance(e, int) for e in sigmas]):
        raise TypeError('Elements of "sigmas" must have type int.')
    if not isinstance(frequencies, set):
        raise TypeError('Argument "frequencies" must have type set.')
    if not all([isinstance(e, float) for e in frequencies]):
        raise TypeError('Elements of "frequencies" must have type float.')
    gabor_kernels = dict()
    for t in range(theta_range):
        theta = t / 4. * np.pi
        for sigma in sigmas:
            for freq in frequencies:
                # Use the real parts of the Gabor filter kernel
                k = np.real(
                        gabor_kernel(
                            freq, theta=theta, sigma_x=sigma, sigma_y=sigma))
                name = 'frequency%.2f-theta%.2f-sigma%d' % (freq, theta, sigma)
                gabor_kernels[name] = k
    return gabor_kernels


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
    features = dict()
    gabor_kernels = get_gabor_kernels()
    for name, kernel in gabor_kernels.items():
        filtered = ndi.convolve(im.astype(float), kernel, mode='wrap')
        features['Gabor_mean-%s' % name] = filtered[mask].mean()
        features['Gabor_var-%s' % name] = filtered[mask].var()
    return features


def measure_surf(im, mask):
    '''
    Calculate statisics based on the Speeded-Up Robust Features (SURF).

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

    See also
    --------
    :py:func:`mahotas.features.surf`
    '''
    if not im.shape == mask.shape:
        raise ValueError('Images must have the same size.')
    if not mask.dtype == 'bool':
        raise TypeError('Mask image must have type bool.')

    points = surf.surf(im, descriptor_only=True)

    features = dict()
    if len(points) == 0:
        features['SURF_n-points'] = 0
        features['SURF_mean-inter-point-distance'] = np.nan
        features['SURF_var-inter-point-distance'] = np.nan
        features['SURF_mean-point-scale'] = np.nan
        features['SURF_var-point-scale'] = np.nan
        features['SURF_mean-descriptor-value'] = np.nan
        features['SURF_var-descriptor-value'] = np.nan
    else:
        # Number of detected interest points
        features['SURF_n-points'] = len(points)
        # Mean distance between interest points normalized for object size
        # (size of the image, which represents the bounding box of the object)
        y = points[:, 0]
        x = points[:, 1]
        coordinates = np.array((y, x)).T
        dist = distance.cdist(coordinates, coordinates)
        features['SURF_mean-inter-point-distance'] = np.mean(dist) / im.size
        features['SURF_var-inter-point-distance'] = np.var(dist) / im.size
        # Mean scale of interest points
        scale = points[:, 2]
        features['SURF_mean-point-scale'] = np.mean(scale)
        features['SURF_var-point-scale'] = np.var(scale)
        descriptors = points[:, 6:]
        features['SURF_mean-descriptor-value'] = np.mean(descriptors)
        features['SURF_var-descriptor-value'] = np.var(descriptors)
    return features
