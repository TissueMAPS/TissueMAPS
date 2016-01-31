import numpy as np
import pandas as pd
import mahotas as mh
import itertools
import h5py
import logging
from abc import ABCMeta
from abc import abstractproperty
from abc import abstractmethod
from cached_property import cached_property
from skimage import measure
from skimage import filters
from mahotas.features import surf
from scipy import ndimage as ndi
from scipy.spatial import distance
from skimage.filters import gabor_kernel
from jtlib import utils

logger = logging.getLogger(__name__)


class Features(object):

    '''
    Abstract base class for the extraction of features from images.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, object_name, label_image,
                 channel_name=None, intensity_image=None):
        '''
        Initialize an instance of class Features.

        Parameters
        ----------
        object_name: str
            name of the objects in `label_image`
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels have zero values and
            and object pixels have a unique identifier value
        channel_name: str, optional
            name of the channel that corresponds to `intensity_image`
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image

        Raises
        ------
        TypeError
            when `intensity_image` doesn't have unsigned integer type
        ValueError
            when `intensity_image` and `label_image` don't have identical shape
        '''
        self.object_name = object_name
        self.label_image = label_image
        self.channel_name = channel_name
        self.intensity_image = intensity_image
        if self.intensity_image is not None:
            if not str(self.intensity_image.dtype).startswith('uint'):
                raise TypeError(
                        'Argument "intensity_image" must have unsigned '
                        'integer type')
            if self.label_image.shape != self.intensity_image.shape:
                raise ValueError(
                        'Arrays "label_image" and "intensity_image" must have '
                        'identical shape.')

    @cached_property
    def names(self):
        '''
        Returns
        -------
        str
            names of the features

        Note
        ----
        Names must adhere to the following naming convention::
            "{object_name}_{feature_group}_{feature}".format()
        '''
        return [
            '{object_name}_{feature_group}_{feature}'.format(
                object_name=self.object_name.capitalize(),
                feature_group=self._feature_group,
                feature=f)
            for f in self._features
        ]

    @abstractproperty
    def _feature_group(self):
        # examples of feature types are "Intensity", "Morphology", "Texture"
        pass

    @abstractproperty
    def _features(self):
        pass

    @abstractmethod
    def extract(self):
        '''
        Extract features from objects.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        pass

    @property
    def object_ids(self):
        '''
        Returns
        -------
        numpy.array[numpy.int]
            one-based unique id of each object in `label_image`
        '''
        return np.unique(self.label_image[self.label_image > 0])

    @property
    def n_objects(self):
        '''
        Returns
        -------
        int
            number of objects in `label_image`
        '''
        return len(self.object_ids)

    def get_object_mask_image(self, object_id):
        '''
        Returns
        -------
        numpy.ndarray[bool]
            mask image for given object; the size of the image depends on
            the bounding box of the object
        '''
        obj = self.object_properties[object_id]
        img = utils.crop_image(self.label_image, bbox=obj.bbox, pad=True)
        mask = img == obj.label
        return mask

    def get_object_intensity_image(self, object_id):
        '''
        Returns
        -------
        numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image for given object; the size of the image depends on
            the bounding box of the object
        '''
        obj = self.object_properties[object_id]
        img = utils.crop_image(self.intensity_image, bbox=obj.bbox, pad=True)
        return img

    @cached_property
    def object_properties(self):
        '''
        Returns
        -------
        Dict[int, skimage.measure._regionprops._RegionProperties]
            mapping of object id to properties for each object in `label_image`
        '''
        logger.debug('measure object properties')
        props = measure.regionprops(
                    self.label_image,
                    intensity_image=self.intensity_image)
        return {region.label: region for region in props}

    def save(self, features, filename):
        '''
        Write values for each extracted feature to a separate dataset in the
        HDF5 file.

        Parameters
        ----------
        features: pandas.DataFrame
            table with dimensions *n*x*p*, where *n* is the number of objects
            and *p* the number of features
        filename: str
            absolute path to the HDF5 file

        Note
        ----
        Dataset is written using `h5py`.
        '''
        logger.debug('save features to HDF5 file')
        with h5py.File(filename) as f:
            for name, values in features.iteritems():
                p = 'objects/%s/features/%s' % (self.object_name, name)
                logger.debug('save dataset "%s"', p)
                f[p] = values

    def plot(self):
        # TODO
        pass


class Intensity(Features):

    def __init__(self, object_name, label_image,
                 channel_name, intensity_image):
        '''
        Initialize an instance of class Features.

        Parameters
        ----------
        object_name: str
            name of the objects in `label_image`
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels have zero values and
            and object pixels have a unique identifier value
        channel_name: str, optional
            name of the channel that corresponds to `intensity_image`
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image
        '''
        super(Intensity, self).__init__(
                object_name, label_image, channel_name, intensity_image)

    @property
    def _feature_group(self):
        return self.__class__.__name__

    @property
    def _features(self):
        feats = ['max', 'mean', 'min', 'sum', 'std']
        return ['%s_%s' % (f, self.channel_name) for f in feats]

    def extract(self):
        '''
        Extract intensity features by measuring maximum, minimum, sum,
        mean and the standard deviation of pixel values within each object
        region in the intensity image.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        # Create an empty dataset in case no objects were detected
        logger.info('extract intensity features for objects "%s" and channel "%s"',
                    self.object_name, self.channel_name)
        features = dict()
        for i, name in enumerate(self.names):
            features[name] = list()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            img = self.get_object_intensity_image(obj)
            # Set all non-object pixels to NaN
            img_nan = img.astype(np.float)
            img_nan[~mask] = np.nan
            region = self.object_properties[obj]
            feats = [
                region.max_intensity,
                region.mean_intensity,
                region.min_intensity,
                np.nansum(img_nan),
                np.nanstd(img_nan),
            ]
            if len(feats) != len(self.names):
                raise IndexError(
                        'Number of features for object %d is incorrect.', obj)
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features)


class Morphology(Features):

    def __init__(self, object_name, label_image):
        '''
        Initialize an instance of class Morphology.

        Parameters
        ----------
        object_name: str
            name of the objects in `label_image`
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels have zero values and
            and object pixels have a unique identifier value
        '''
        super(Morphology, self).__init__(object_name, label_image)

    @property
    def _feature_group(self):
        return self.__class__.__name__

    @property
    def _features(self):
        return [
            'area',
            'eccentricity',
            'solidity',
            'form-factor'
        ]

    def extract(self):
        '''
        Extract morphology features, such as the size and the shape of
        each object in the image.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        # Create an empty dataset in case no objects were detected
        features = dict()
        for i, name in enumerate(self.names):
            features[name] = list()
        for obj in self.object_ids:
            region = self.object_properties[obj]
            feats = [
                region.area,
                region.eccentricity,
                region.solidity,
                (4.0 * np.pi * region.area) / (region.perimeter**2),
            ]
            if len(feats) != len(self.names):
                raise IndexError(
                        'Number of features for object %d is incorrect.', obj)
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features)


class Haralick(Features):

    '''
    Class for calculating Haralick texture features based on Haralick [1]_.

    References
    ----------
    ..[1] Haralick R.M. (1979): "Statistical and structural approaches to texture". Proceedings of the IEEE
    '''

    def __init__(self, object_name, label_image,
                 channel_name, intensity_image):
        '''
        Initialize an instance of class Haralick.

        Parameters
        ----------
        object_name: str
            name of the objects in `label_image`
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels have zero values and
            and object pixels have a unique identifier value
        channel_name: str, optional
            name of the channel that corresponds to `intensity_image`
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image

        Note
        ----
        Computation of Haralick features is computational intensive and may
        require a lot of memory, in particular for 16 bit images. Therefore,
        the `intensity_image` is streched to the range [0, 255].
        For further details see
        `Mahotas FAQs <http://mahotas.readthedocs.org/en/latest/faq.html#i-ran-out-of-memory-computing-haralick-features-on-16-bit-images-is-it-not-supported>`_  
        '''
        intensity_image = mh.stretch(intensity_image)
        super(Haralick, self).__init__(
                object_name, label_image, channel_name, intensity_image)

    @property
    def _feature_group(self):
        return self.__class__.__name__

    @property
    def _features(self):
        feats = [
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
        return ['%s_%s' % (f, self.channel_name) for f in feats]

    def extract(self):
        '''
        Extract Haralick texture features.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`

        See also
        --------
        :py:func:`mahotas.features.haralick`
        '''
        # Create an empty dataset in case no objects were detected
        features = dict()
        for i, name in enumerate(self.names):
            features[name] = list()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            img = self.get_object_intensity_image(obj)
            # Set all non-object pixels to zero
            img[~mask] = 0
            feats = mh.features.haralick(
                        img, ignore_zeros=True, return_mean=True)
            if len(feats) != len(self.names):
                raise IndexError(
                        'Number of features for object %d is incorrect.', obj)
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features)


class TAS(Features):

    '''
    Class for calculating Threshold Adjacency Statistics based on
    Hamilton [1]_.

    References
    ----------
    .. [1] Hamilton N.A. et al. (2007): "Fast automated cell phenotype image classification". BMC Bioinformatics
    '''

    def __init__(self, object_name, label_image,
                 channel_name, intensity_image):
        '''
        Initialize an instance of class TAS.

        Parameters
        ----------
        object_name: str
            name of the objects in `label_image`
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels have zero values and
            and object pixels have a unique identifier value
        channel_name: str, optional
            name of the channel that corresponds to `intensity_image`
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image
        '''
        super(TAS, self).__init__(
                object_name, label_image, channel_name, intensity_image)
        self.threshold = filters.threshold_otsu(intensity_image)

    @property
    def _feature_group(self):
        return self.__class__.__name__

    @property
    def _features(self):
        feats = ['center-%s' % i for i in xrange(9)] + \
                ['n-center-%s' % i for i in xrange(9)] + \
                ['mu-margin-%s' % i for i in xrange(9)] + \
                ['n-mu-margin-%s' % i for i in xrange(9)] + \
                ['mu-%s' % i for i in xrange(9)] + \
                ['n-mu-%s' % i for i in xrange(9)]
        return ['%s_%s' % (f, self.channel_name) for f in feats]

    def extract(self):
        '''
        Extract Threshold Adjacency Statistics.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`

        See also
        --------
        :py:func:`mahotas.features.haralick`
        '''
        # Create an empty dataset in case no objects were detected
        features = dict()
        for i, name in enumerate(self.names):
            features[name] = list()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            img = self.get_object_intensity_image(obj)
            # Set all non-object pixels to zero
            img[~mask] = 0
            feats = mh.features.pftas(img, T=self.threshold)
            if len(feats) != len(self.names):
                raise IndexError(
                        'Number of features for object %d is incorrect.', obj)
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features)


class Gabor(Features):

    '''
    Class for calculating Gabor texture features.
    '''

    def __init__(self, object_name, label_image,
                 channel_name, intensity_image,
                 theta_range=4, sigmas={1, 3}, frequencies={0.05, 0.25}):
        '''
        Initialize an instance of class Gabor.

        Parameters
        ----------
        object_name: str
            name of the objects in `label_image`
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels have zero values and
            and object pixels have a unique identifier value
        channel_name: str, optional
            name of the channel that corresponds to `intensity_image`
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image
        theta_range: int
            number of `theta` values for Garbor kernels
        sigmas: Set[int]
            values for `sigma_x` and `sigma_y` for Garbor kernels
        frequencies: Set[float]
            values for `frequency` for Garbor kernels
        '''
        super(Gabor, self).__init__(
                object_name, label_image, channel_name, intensity_image)
        self.thetas = [t / 4. * np.pi for t in range(theta_range)]
        self.sigmas = sigmas
        self.frequencies = frequencies

    @property
    def _feature_group(self):
        return self.__class__.__name__

    @property
    def _features(self):
        feats = list()
        for f, t, s in itertools.product(self.frequencies, self.thetas, self.sigmas):
            feats.append('mean-frequency%.2f-theta%.2f-sigma%d' % (f, t, s))
            feats.append('var-frequency%.2f-theta%.2f-sigma%d' % (f, t, s))
        return ['%s_%s' % (f, self.channel_name) for f in feats]

    def extract(self):
        '''
        Extract Gabor texture features by filtering the intensity image with
        Gabor kernels for a defined range of `frequency`, `sigma` and `theta`
        values and calculating the mean and variance of pixel values within
        each object region in the filtered images.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`

        See also
        --------
        :py:func:`skimage.filters.gabor_kernel`
        '''
        # Create an empty dataset in case no objects were detected
        features = dict()
        for i, name in enumerate(self.names):
            features[name] = list()
        kernels = self._get_kernels()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            img = self.get_object_intensity_image(obj)
            feats = list()
            for k in kernels:
                # see also: skimage.filters.gabor()
                img_filtered = ndi.convolve(img.astype(float), k, mode='wrap')
                feats.append(img_filtered[mask].mean())
                feats.append(img_filtered[mask].var())
            if len(feats) != len(self.names):
                raise IndexError(
                        'Number of features for object %d is incorrect.', obj)
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features)

    def _get_kernels(self):
        kernels = list()
        for f, t, s in itertools.product(self.frequencies, self.thetas, self.sigmas):
            # Use the real parts of the Gabor filter kernel
            k = np.real(gabor_kernel(f, theta=t, sigma_x=s, sigma_y=s))
            kernels.append(k)
        return kernels


class Hu(Features):

    '''
    Class for calculating Hu moments based on Hu [1]_.

    Refernces
    ---------
    ..[1] M. K. Hu (1962): "Visual Pattern Recognition by Moment Invariants", IRE Trans. Info. Theory
    '''

    def __init__(self, object_name, label_image,
                 channel_name, intensity_image):
        '''
        Initialize an instance of class Hu.

        Parameters
        ----------
        object_name: str
            name of the objects in `label_image`
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels have zero values and
            and object pixels have a unique identifier value
        channel_name: str, optional
            name of the channel that corresponds to `intensity_image`
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image
        '''
        super(Hu, self).__init__(
                object_name, label_image, channel_name, intensity_image)

    @property
    def _feature_group(self):
        return self.__class__.__name__

    @property
    def _features(self):
        feats = map(str, range(7))
        return ['%s_%s' % (f, self.channel_name) for f in feats]

    def extract(self):
        '''
        Extract Hu moments.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        # Create an empty dataset in case no objects were detected
        features = dict()
        for i, name in enumerate(self.names):
            features[name] = list()
        for obj in self.object_ids:
            region = self.object_properties[obj]
            feats = region.weighted_moments_hu
            if len(feats) != len(self.names):
                raise IndexError(
                        'Number of features for object %d is incorrect.', obj)
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features)


class Zernike(Features):

    '''
    Class for calculating Zernike moments.
    '''

    def __init__(self, object_name, label_image):
        '''
        Initialize an instance of class Zernike.

        Parameters
        ----------
        object_name: str
            name of the objects in `label_image`
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels have zero values and
            and object pixels have a unique identifier value
        '''
        super(Zernike, self).__init__(object_name, label_image)
        self.degree = 12

    @property
    def _feature_group(self):
        return self.__class__.__name__

    @property
    def _features(self):
        feats = list()
        for n in xrange(self.degree+1):
            for l in xrange(n+1):
                if (n-l) % 2 == 0:
                    feats.append('%s-%s' % (n, l))
        return feats

    def extract(self, radius=100):
        '''
        Extract Zernike moments.

        Parameters
        ----------
        radius: int, optional
            radius for rescaling of images (default: ``100``) to achieve
            scale invariance

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        # Create an empty dataset in case no objects were detected
        features = dict()
        for i, name in enumerate(self.names):
            features[name] = list()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            mask_rs = mh.imresize(mask, [radius*2, radius*2])
            feats = mh.features.zernike_moments(
                            mask_rs, degree=self.degree, radius=radius)
            if len(feats) != len(self.names):
                raise IndexError(
                        'Number of features for object %d is incorrect.', obj)
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features)


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
