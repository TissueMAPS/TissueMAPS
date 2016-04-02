import numpy as np
import pandas as pd
import mahotas as mh
import logging
from abc import ABCMeta
from abc import abstractproperty
from abc import abstractmethod
from cached_property import cached_property
from skimage import measure
from skimage import filters
from scipy import ndimage as ndi
# from mahotas.features import surf
# from scipy.spatial import distance
from centrosome.filter import gabor
from jtlib import utils

logger = logging.getLogger(__name__)


class Features(object):

    '''Abstract base class for the extraction of features from images.'''

    __metaclass__ = ABCMeta

    def __init__(self, label_image, intensity_image=None):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels are zero and
            and pixels belonging to a segmented object (connected component)
            are labeled with a unique identifier value
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8], optional
            intensity image (default: ``None``)

        Raises
        ------
        TypeError
            when `intensity_image` doesn't have unsigned integer type
        ValueError
            when `intensity_image` and `label_image` don't have identical shape
        '''
        self.label_image = label_image
        self.intensity_image = intensity_image
        if self.intensity_image is not None:
            if not str(self.intensity_image.dtype).startswith('uint'):
                raise TypeError(
                    'Argument "intensity_image" must have unsigned '
                    'integer type'
                )
            if self.label_image.shape != self.intensity_image.shape:
                raise ValueError(
                    'Arrays "label_image" and "intensity_image" must have '
                    'identical shape.'
                )

    @cached_property
    def names(self):
        '''List[str]: names of the features'''
        return [
            '{feature_group}_{feature_name}'.format(
                feature_group=self._feature_group, feature_name=f
            )
            for f in self._feature_names
        ]

    @property
    def _feature_group(self):
        return self.__class__.__name__

    @abstractproperty
    def _feature_names(self):
        pass

    @abstractmethod
    def extract(self):
        '''Extracts features for segmented objects.

        Returns
        -------
        pandas.DataFrame[float]
            extracted feature values for each object in `label_image`

        Note
        ----
        The index must match the object labels in the range [1, *n*], where
        *n* is the number of segmented objects.
        '''
        pass

    @property
    def object_ids(self):
        '''numpy.array[numpy.int]: one-based unique id of each object in
        `label_image`'''
        return np.unique(self.label_image[self.label_image > 0])

    @property
    def n_objects(self):
        '''int: number of objects in `label_image`'''
        return len(self.object_ids)

    def get_object_mask_image(self, object_id):
        '''Extracts the bounding box for a given object from `label_image`.

        Returns
        -------
        numpy.ndarray[bool]
            mask image for given object
        '''
        obj = self.object_properties[object_id]
        img = utils.crop_image(self.label_image, bbox=obj.bbox, pad=True)
        return img == obj.label

    def get_object_intensity_image(self, object_id):
        '''Extracts the bounding box for a given object from `intensity_image`.

        Returns
        -------
        numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image for given object; the size of the image is
            determined by the bounding box of the object
        '''
        obj = self.object_properties[object_id]
        return utils.crop_image(self.intensity_image, bbox=obj.bbox, pad=True)

    @cached_property
    def object_properties(self):
        '''Dict[int, skimage.measure._regionprops._RegionProperties]: mapping
        of object id to properties for each object in `label_image`
        '''
        logger.debug('measure object properties')
        props = measure.regionprops(
            self.label_image, intensity_image=self.intensity_image
        )
        return {region.label: region for region in props}

    def plot(self):
        # TODO
        pass


class Intensity(Features):

    def __init__(self, label_image, intensity_image):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels are zero and
            and pixels belonging to a segmented object (connected component)
            are labeled with a unique identifier value
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image
        '''
        super(Intensity, self).__init__(label_image, intensity_image)

    @property
    def _feature_names(self):
        return ['max', 'mean', 'min', 'sum', 'std']

    def extract(self):
        '''Extracts intensity features by measuring maximum, minimum, sum,
        mean and the standard deviation of pixel values within each object
        region in the intensity image.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        # Create an empty dataset in case no objects were detected
        logger.info('extract intensity features ')
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
        return pd.DataFrame(features, index=self.object_ids)


class Morphology(Features):

    def __init__(self, label_image):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels are zero and
            and pixels belonging to a segmented object (connected component)
            are labeled with a unique identifier value
        '''
        super(Morphology, self).__init__(label_image)

    @property
    def _feature_names(self):
        return [
            'area', 'eccentricity', 'solidity', 'form-factor'
        ]

    def extract(self):
        '''Extracts morphology features, such as the size and the shape of
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
        return pd.DataFrame(features, index=self.object_ids)


class Haralick(Features):

    '''
    Class for calculating Haralick texture features based on Haralick [1]_.

    References
    ----------
    ..[1] Haralick R.M. (1979): "Statistical and structural approaches to texture". Proceedings of the IEEE
    '''

    def __init__(self, label_image, intensity_image):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels are zero and
            and pixels belonging to a segmented object (connected component)
            are labeled with a unique identifier value
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image

        Note
        ----
        Computation of Haralick features is computational intensive and may
        require a lot of memory, in particular for 16 bit images. Therefore,
        the `intensity_image` is "stretched" to the range [0, 255].
        For further details see
        `Mahotas FAQs <http://mahotas.readthedocs.org/en/latest/faq.html#i-ran-out-of-memory-computing-haralick-features-on-16-bit-images-is-it-not-supported>`_  
        '''
        intensity_image = mh.stretch(intensity_image)
        super(Haralick, self).__init__(label_image, intensity_image)

    @property
    def _feature_names(self):
        return [
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

    def extract(self):
        '''Extracts Haralick texture features.

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
            img = self.get_object_intensity_image(obj)  # TODO: normalize
            # Set all non-object pixels to zero
            img[~mask] = 0
            feats = mh.features.haralick(
                        img, ignore_zeros=False, return_mean=True)
            # TODO: the output changed in the latest version of Mahotas
            if not isinstance(feats, np.ndarray):
                # NOTE: setting `ignore_zeros` to True creates problems for some
                # objects, when all values of the adjacency matrices are zeros
                feats = np.empty((13, ), dtype=float)
                feats[:] = np.NAN
            if len(feats) != len(self.names):
                raise IndexError(
                        'Number of features for object %d is incorrect.', obj)
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features, index=self.object_ids)


class TAS(Features):

    '''Class for calculating Threshold Adjacency Statistics based on
    Hamilton [1]_.

    References
    ----------
    .. [1] Hamilton N.A. et al. (2007): "Fast automated cell phenotype image classification". BMC Bioinformatics
    '''

    def __init__(self, label_image, intensity_image):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels are zero and
            and pixels belonging to a segmented object (connected component)
            are labeled with a unique identifier value
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image
        '''
        super(TAS, self).__init__(label_image, intensity_image)
        self.threshold = filters.threshold_otsu(intensity_image)

    @property
    def _feature_names(self):
        return (
            ['center-%s' % i for i in xrange(9)] +
            ['n-center-%s' % i for i in xrange(9)] +
            ['mu-margin-%s' % i for i in xrange(9)] +
            ['n-mu-margin-%s' % i for i in xrange(9)] +
            ['mu-%s' % i for i in xrange(9)] +
            ['n-mu-%s' % i for i in xrange(9)]
        )

    def extract(self):
        '''Extracts Threshold Adjacency Statistics.

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
                    'Number of features for object %d is incorrect.', obj
                )
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features, index=self.object_ids)


class Gabor(Features):

    '''Class for calculating Gabor texture features.'''

    def __init__(self, label_image, intensity_image,
                 theta_range=4, frequencies={1, 5, 10}):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels are zero and
            and pixels belonging to a segmented object (connected component)
            are labeled with a unique identifier value
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image
        theta_range: int, optional
            number of angles to define the orientations of the Gabor
            filters (default: 4)
        frequencies: Set[float], optional
            frequencies of the Gabor filters
        '''
        super(Gabor, self).__init__(label_image, intensity_image)
        self.theta_range = theta_range
        self.frequencies = frequencies

    @property
    def _feature_names(self):
        return ['frequency-%.2f' % f for f in self.frequencies]

    def extract(self):
        '''Extracts Gabor texture features by filtering the intensity image with
        Gabor kernels for a defined range of `frequency` and `theta` values and
        then calculating a score for each object.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`

        See also
        --------
        :py:class:`cellprofiler.modules.measuretexture.MeasureTexture`
        :py:func:`centrosome.filter.gabor`
        '''
        # Create an empty dataset in case no objects were detected
        features = dict()
        for i, name in enumerate(self.names):
            features[name] = list()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            label = mask.astype(np.int32)
            img = self.get_object_intensity_image(obj)
            feats = list()
            for freq in self.frequencies:
                best_score = 0
                for angle in range(self.theta_range):
                    theta = np.pi * angle / self.theta_range
                    g = gabor(img, label, freq, theta)
                    score_r = ndi.measurements.sum(
                        g.real, label, np.arange(1, dtype=np.int32) + 1
                    )
                    score_i = ndi.measurements.sum(
                        g.imag, label, np.arange(1, dtype=np.int32) + 1
                    )
                    score = np.sqrt(score_r**2 + score_i**2)
                    best_score = np.max([best_score, score])
                feats.append(best_score)
            if len(feats) != len(self.names):
                raise IndexError(
                    'Number of features for object %d is incorrect.', obj
                )
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features, index=self.object_ids)


class Hu(Features):

    '''Class for calculating Hu moments based on Hu [1]_.

    Refernces
    ---------
    ..[1] M. K. Hu (1962): "Visual Pattern Recognition by Moment Invariants", IRE Trans. Info. Theory
    '''

    def __init__(self, label_image, intensity_image):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels are zero and
            and pixels belonging to a segmented object (connected component)
            are labeled with a unique identifier value
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image
        '''
        super(Hu, self).__init__(label_image, intensity_image)

    @property
    def _feature_names(self):
        return map(str, range(7))

    def extract(self):
        '''Extracts Hu moments.

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
        return pd.DataFrame(features, index=self.object_ids)


class Zernike(Features):

    '''Class for calculating Zernike moments.'''

    def __init__(self, label_image, radius=100):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image, where background pixels are zero and
            and pixels belonging to a segmented object (connected component)
            are labeled with a unique identifier value
        radius: int, optional
            radius for rescaling of images to achieve scale invariance
            (default: ``100``)
        '''
        super(Zernike, self).__init__(label_image)
        self.radius = radius
        self.degree = 12

    @property
    def _feature_names(self):
        feats = list()
        for n in xrange(self.degree+1):
            for l in xrange(n+1):
                if (n-l) % 2 == 0:
                    feats.append('%s-%s' % (n, l))
        return feats

    def extract(self):
        '''Extracts Zernike moments.

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
            mask_rs = mh.imresize(mask, [self.radius*2, self.radius*2])
            feats = mh.features.zernike_moments(
                mask_rs, degree=self.degree, radius=self.radius
            )
            if len(feats) != len(self.names):
                raise IndexError(
                    'Number of features for object %d is incorrect.', obj
                )
            for i, name in enumerate(self.names):
                features[name].append(feats[i])
        return pd.DataFrame(features, index=self.object_ids)


# def measure_surf(im, mask):
#     '''
#     Calculate statisics based on the Speeded-Up Robust Features (SURF).

#     Parameters
#     ----------
#     im: numpy.ndarray[int]
#         intensity image
#     mask: numpy.ndarray[bool]
#         mask image containing one object (i.e. one connected pixel component);
#         must have the same size as `im`

#     Returns
#     -------
#     dict
#         features

#     Raises
#     ------
#     ValueError
#         when `im` and `mask` don't have the same size
#     TypeError
#         when elements of `mask` don't have type bool

#     See also
#     --------
#     :py:func:`mahotas.features.surf`
#     '''
#     if not im.shape == mask.shape:
#         raise ValueError('Images must have the same size.')
#     if not mask.dtype == 'bool':
#         raise TypeError('Mask image must have type bool.')

#     points = surf.surf(im, descriptor_only=True)

#     features = dict()
#     if len(points) == 0:
#         features['SURF_n-points'] = 0
#         features['SURF_mean-inter-point-distance'] = np.nan
#         features['SURF_var-inter-point-distance'] = np.nan
#         features['SURF_mean-point-scale'] = np.nan
#         features['SURF_var-point-scale'] = np.nan
#         features['SURF_mean-descriptor-value'] = np.nan
#         features['SURF_var-descriptor-value'] = np.nan
#     else:
#         # Number of detected interest points
#         features['SURF_n-points'] = len(points)
#         # Mean distance between interest points normalized for object size
#         # (size of the image, which represents the bounding box of the object)
#         y = points[:, 0]
#         x = points[:, 1]
#         coordinates = np.array((y, x)).T
#         dist = distance.cdist(coordinates, coordinates)
#         features['SURF_mean-inter-point-distance'] = np.mean(dist) / im.size
#         features['SURF_var-inter-point-distance'] = np.var(dist) / im.size
#         # Mean scale of interest points
#         scale = points[:, 2]
#         features['SURF_mean-point-scale'] = np.mean(scale)
#         features['SURF_var-point-scale'] = np.var(scale)
#         descriptors = points[:, 6:]
#         features['SURF_mean-descriptor-value'] = np.mean(descriptors)
#         features['SURF_var-descriptor-value'] = np.var(descriptors)
#     return features
