# Copyright 2016 Markus D. Herrmann, University of Zurich
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import numpy as np
import pandas as pd
import mahotas as mh
import logging
import collections
from abc import ABCMeta
from abc import abstractproperty
from abc import abstractmethod
from cached_property import cached_property
from skimage import measure
from skimage import filters
from scipy import ndimage as ndi
# from mahotas.features import surf
from scipy.spatial.distance import squareform, pdist
from centrosome.filter import gabor
from jtlib import utils


logger = logging.getLogger(__name__)


class Features(object):

    '''Abstract base class for the extraction of features from images.

    Warning
    -------
    Currently only implemented for 2D images!
    '''

    __metaclass__ = ABCMeta

    def __init__(self, label_image, intensity_image=None):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image encoding objects (connected pixel components)
            for which features should be extracted
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            grayscale image from which texture features should be extracted
            (default: ``None``)

        Raises
        ------
        TypeError
            when `intensity_image` doesn't have unsigned integer type
        ValueError
            when `intensity_image` and `label_image` don't have identical shape
            or when `label_image` is not 2D
        '''
        self.label_image = label_image
        if len(label_image.shape) > 2:
            raise ValueError(
                'Feature extraction is only implemented for 2D images.'
            )
        self.intensity_image = intensity_image
        if self.intensity_image is not None:
            if not str(self.intensity_image.dtype).startswith('uint'):
                raise TypeError(
                    'Argument "intensity_image" must have unsigned '
                    'integer type'
                )
            if self.label_image.shape != self.intensity_image.shape:
                raise ValueError(
                    'Images "label_image" and "intensity_image" must have '
                    'the same dimensions.'
                )

    @cached_property
    def names(self):
        '''List[str]: names of features that should be extracted from
        :attr:`label_image <jtlib.featues.Features.label_image>`
        '''
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

    @cached_property
    def _aggregate_statistics(self):
        '''Dict[str, function]: mapping of statistics name to corresponding
        function that can be used to compute the statistic
        '''
        return {
            'Mean': np.nanmean,
            'Std': np.nanstd,
            'Sum': np.nansum,
        }

    def check_assignment(self, ref_label_image, aggregate):
        '''Determines whether aggregation of features is required in order to
        assign the values to objects in `ref_label_image`.

        Parameters
        ----------
        ref_label_image: numpy.ndarray[numpy.int32]
            reference label image to which feature values should be assigned
        aggregate: bool
            whether feature values should be aggregated

        Raises
        ------
        ValueError
            when assignment of feature values to objects is not possible
        '''
        if self.label_image.shape != ref_label_image.shape:
            raise ValueError(
                'Image "ref_label_image" has incorrect dimensions.'
            )
        if not aggregate:
            if np.any((self.label_image - ref_label_image) > 0):
                raise ValueError(
                    'Should this be an aggregate measurement?'
                    'Some assigned objects contain more than one of the objects'
                    'that measurements are extracted for'
                    '(e.g. multiple disconnected parts of the cytoplasm for one cell)'
                )
        else:
            if np.any(self.label_image[ref_label_image == 0] > 0):
                raise ValueError(
                    'All objects must be contained by objects in '
                    '"ref_label_image".'
                )

    def extract_aggregate(self, ref_label_image):
        '''Extracts aggregate features for segmented objects.

        Parameters
        ----------
        ref_label_image: numpy.ndarray[numpy.int32]
            reference label image encoding objects to which computed aggregate
            features should be assigned

        Returns
        -------
        pandas.DataFrame[float]
            extracted feature values for each object in `ref_label_image`
            *n*x*p* dataframe, where *n* is the number of objects and
            *p* is the number of features times the number of aggregate
            statistics computed for each feature
        '''
        values = collections.defaultdict(list)
        features = self.extract()
        ref_object_ids = np.unique(ref_label_image)[1:]
        for ref_label in ref_object_ids:
            labels = np.unique(self.label_image[ref_label_image == ref_label])
            labels = labels[labels > 0]
            values['Count'].append(len(labels))
            if len(labels) == 0:
                for name in features.columns:
                    for stat in self._aggregate_statistics.keys():
                        values['%s_%s' % (stat, name)].append(np.nan)
            else:
                index = np.union1d(features.index, labels)
                diff = len(labels) - len(index)
                if diff > 0:
                    logger.warn('%d objects got lost upon aggregation', diff)
                for name, vals in features.loc[index, :].iteritems():
                    if vals.empty:
                        for stat in self._aggregate_statistics.keys:
                            values['%s_%s' % (stat, name)].append(np.nan)
                    else:
                        for stat, func in self._aggregate_statistics.iteritems():
                            values['%s_%s' % (stat, name)].append(
                                float(func(vals))
                            )
        return pd.DataFrame(values, index=ref_object_ids)

    @abstractmethod
    def extract(self):
        '''Extracts features for segmented objects.

        Returns
        -------
        pandas.DataFrame[float]
            extracted feature values for each object in
            :attr:`label_image <jtlib.featues.Features.label_image>`;
            *n*x*p* dataframe, where *n* is the number of objects and
            *p* is the number of features

        Note
        ----
        The index must match the object labels in the range [1, *n*], where
        *n* is the number of objects in
        :attr:`label_image <jtlib.featues.Features.label_image>`.
        '''
        pass

    @property
    def object_ids(self):
        '''numpy.array[numpy.int]: label of each object in
        :attr:`label_image <jtlib.features.Features.label_image>`.
        '''
        return np.unique(self.label_image[self.label_image > 0])

    @property
    def n_objects(self):
        '''int: number of objects in
        :attr:`label_image <jtlib.features.Features.label_image>`.
        '''
        return len(self.object_ids)

    def get_object_mask_image(self, object_id):
        '''Extracts the bounding box for a given object from
        :attr:`label_image <jtlib.features.Features.label_image>`.

        Returns
        -------
        numpy.ndarray[bool]
            mask image for given object
        '''
        bbox = self._bboxes[object_id]
        img = utils.extract_bbox(self.label_image, bbox=bbox, pad=1)
        return img == object_id

    def get_object_intensity_image(self, object_id):
        '''Extracts the bounding box for a given object from
        :attr:`intensity_image <jtlib.features.Features.intensity_image>`.

        Returns
        -------
        numpy.ndarray[numpy.uint16 or numpy.uint8]
            intensity image for given object; the size of the image is
            determined by the bounding box of the object
        '''
        if self.intensity_image is None:
            raise ValueError('No intensity image available.')
        bbox = self._bboxes[object_id]
        return utils.extract_bbox(self.intensity_image, bbox=bbox, pad=1)

    @cached_property
    def _bboxes(self):
        '''List[numpy.ndarray]: bounding boxes for each object in
        :attr:`label_image <jtlib.features.Features.label_image>`.
        '''
        return mh.labeled.bbox(self.label_image)

    @cached_property
    def object_properties(self):
        '''Dict[int, skimage.measure._regionprops._RegionProperties]: mapping
        of object id to properties for each object in
        :attr:`label_image <jtlib.features.Features.label_image>`.
        '''
        logger.debug('measure object properties')
        props = measure.regionprops(
            self.label_image, intensity_image=self.intensity_image
        )
        return {region.label: region for region in props}

    def plot(self):
        # TODO
        logger.warn('no plot created: not yet implemented')
        return str()


class Intensity(Features):

    '''Class for calculating intensity statistics, such as mean and variation
    of pixel values within segmented objects.

    '''

    def __init__(self, label_image, intensity_image):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image encoding objects (connected pixel components)
            for which features should be extracted
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            grayscale image from which texture features should be extracted
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
        logger.info('extract intensity features')
        features = list()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            img = self.get_object_intensity_image(obj)
            # Set all non-object pixels to NaN
            img_nan = img.astype(np.float)
            img_nan[~mask] = np.nan
            region = self.object_properties[obj]
            values = [
                region.max_intensity,
                region.mean_intensity,
                region.min_intensity,
                np.nansum(img_nan),
                np.nanstd(img_nan),
            ]
            features.append(values)
        return pd.DataFrame(features, columns=self.names, index=self.object_ids)


class Morphology(Features):

    '''Class for extracting morphology features.'''

    def __init__(self, label_image, compute_zernike=False):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image encoding objects (connected pixel components)
            for which features should be extracted
        compute_zernike: bool, optional
            whether Zernike moments should be computed (default: ``False``)
        '''
        super(Morphology, self).__init__(label_image)
        self._degree = 12
        self.compute_zernike = compute_zernike

    @property
    def _feature_names(self):
        names = [
            'Area', 'Eccentricity', 'Convexity', 'Circularity', 'Perimeter',
            'Elongation'
        ]
        if self.compute_zernike:
            for n in xrange(self._degree+1):
                for m in xrange(n+1):
                    if (n-m) % 2 == 0:
                        names.append('Zernike-%s-%s' % (n, m))
        return names

    def extract(self):
        '''Extracts morphology features to measure the size and shape of objects.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        logger.info('extract morphology features')
        features = list()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            area = np.float64(np.count_nonzero(mask))
            perimeter = mh.labeled.perimeter(mask)
            if perimeter == 0:
                circularity = np.nan
            else:
                circularity = (4.0 * np.pi * area) / (perimeter**2)
            convex_hull = mh.polygon.fill_convexhull(mask)
            area_convex_hull = np.count_nonzero(convex_hull)
            convexity = area / area_convex_hull
            eccentricity = mh.features.eccentricity(mask)
            major_axis, minor_axis = mh.features.ellipse_axes(mask)
            if major_axis == 0:
                elongation = np.nan
            else:
                elongation = (major_axis - minor_axis) / major_axis
            values = [
                area, eccentricity, convexity, circularity, perimeter,
                elongation
            ]
            if self.compute_zernike:
                logger.debug('extract Zernike moments for object #%d', obj)
                r = 100
                mask_rs = mh.imresize(mask, [r*2, r*2])
                zernike_values = mh.features.zernike_moments(
                    mask_rs, degree=self._degree, radius=r
                )
                values.extend(zernike_values)
            features.append(values)
        return pd.DataFrame(features, columns=self.names, index=self.object_ids)


class Texture(Features):

    '''Class for calculating texture features based on Haralick [1]_,
    Gabor [2], Hu [3]_, Threshold Adjancency Statistics (TAS) [4]_ and
    Local Binary Patterns [5]_.

    References
    ----------
    .. [1] Haralick R.M. (1979). "Statistical and structural approaches to texture". Proceedings of the IEEE
    .. [2] Fogel I. et al. (1989). "Gabor filters as texture discriminator". Biological Cybernetics
    .. [3] Hu M.K. (1962). "Visual Pattern Recognition by Moment Invariants", IRE Trans. Info. Theory
    .. [4] Hamilton N.A. et al. (2007). "Fast automated cell phenotype image classification". BMC Bioinformatics
    .. [5] Ojala T. et al. (2000). "Gray Scale and Rotation Invariant Texture Classification with Local Binary Patterns". Lecture Notes in Computer Science

    Note
    ----
    Computation of Haralick features is computational intensive and may
    require a lot of memory, in particular for 16 bit images. Therefore,
    the `intensity_image` is "stretched" to the range [0, 255].
    For further details see
    `Mahotas FAQs <http://mahotas.readthedocs.org/en/latest/faq.html#i-ran-out-of-memory-computing-haralick-features-on-16-bit-images-is-it-not-supported>`_.
    '''

    def __init__(self, label_image, intensity_image,
            theta_range=4, frequencies={1, 5, 10}, radius={1, 5, 10},
            threshold=None, compute_haralick=False):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image encoding objects (connected pixel components)
            for which features should be extracted
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            grayscale image from which texture features should be extracted
        theta_range: int, optional
            number of angles to define the orientations of the Gabor
            filters (default: ``4``)
        frequencies: Set[int], optional
            frequencies of the Gabor filters (default: ``{1, 5, 10}``)
        threshold: int, optional
            threshold value for Threshold Adjacency Statistics (TAS)
            (defaults to value computed by Otsu's method)
        radius: Set[int], optional
            radius for defining pixel neighbourhood for Local Binary Patterns
            (LBP) (default: ``{1, 5, 10}``)
        compute_haralick: bool, optional
            whether Haralick features should be computed
            (the computation is computationally expensive) (default: ``False``)
        '''
        super(Texture, self).__init__(label_image, intensity_image)
        self.theta_range = theta_range
        self.frequencies = frequencies
        self.radius = radius
        if threshold is None:
            self._threshold = mh.otsu(intensity_image)
        else:
            if not isinstance(threshold, int):
                raise ValueError('Argument "threshold" must have type int.')
            self._threshold = threshold
        self._clip_value = np.percentile(intensity_image, 99.999)
        if not isinstance(theta_range, int):
            raise TypeError(
                'Argument "theta_range" must have type int.'
            )
        if not all([isinstance(f, int) for f in self.frequencies]):
            raise TypeError(
                'Elements of argument "frequencies" must have type int.'
            )
        self.compute_haralick = compute_haralick

    @property
    def _feature_names(self):
        names = ['Gabor-frequency-%d' % f for f in self.frequencies]
        names.extend(['TAS-center-%d' % i for i in xrange(9)])
        names.extend(['TAS-n-center-%d' % i for i in xrange(9)])
        names.extend(['TAS-mu-margin-%d' % i for i in xrange(9)])
        names.extend(['TAS-n-mu-margin-%d' % i for i in xrange(9)])
        names.extend(['TAS-mu-%d' % i for i in xrange(9)])
        names.extend(['TAS-n-mu-%d' % i for i in xrange(9)])
        names.extend(['Hu-%d' % i for i in xrange(7)])
        for r in self.radius:
            names.extend(['LBP-radius-%d-%d' % (r, i) for i in xrange(36)])
        if self.compute_haralick:
            names.extend([
                'Haralick-angular-second-moment',
                'Haralick-contrast',
                'Haralick-correlation',
                'Haralick-sum-of-squares',
                'Haralick-inverse-diff-moment',
                'Haralick-sum-avg',
                'Haralick-sum-var',
                'Haralick-sum-entropy',
                'Haralick-entropy',
                'Haralick-diff-var',
                'Haralick-diff-entropy',
                'Haralick-info-measure-corr-1',
                'Haralick-info-measure-corr-2'
            ])
        return names

    def extract(self):
        '''Extracts Gabor texture features by filtering the intensity image with
        Gabor kernels for a defined range of `frequency` and `theta` values and
        then calculating a score for each object.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        # Create an empty dataset in case no objects were detected
        logger.info('extract texture features')
        features = list()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            label = mask.astype(np.int32)
            img = self.get_object_intensity_image(obj)
            img[~mask] = 0
            values = list()
            # Gabor
            logger.debug('extract Gabor features for object #%d', obj)
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
                values.append(best_score)
            # Threshold Adjacency Statistics
            logger.debug('extract TAS features for object #%d', obj)
            tas_values = mh.features.pftas(img, T=self._threshold)
            values.extend(tas_values)
            # Hu
            logger.debug('extract Hu moments for object #%d', obj)
            region = self.object_properties[obj]
            hu_values = region.weighted_moments_hu
            values.extend(hu_values)
            # Local Binary Pattern
            logger.debug('extract Local Binary Patterns for object #%d', obj)
            for r in self.radius:
                # We may want to use more points, but the number of features
                # increases exponentially with the number of neighbourhood
                # points.
                vals = mh.features.lbp(img, radius=r, points=8)
                values.extend(vals)
            if self.compute_haralick:
                # Haralick
                logger.debug('extract Haralick features for object #%d', obj)
                # NOTE: Haralick features are computed on 8-bit images.
                clipped_img = np.clip(img, 0, self._clip_value)
                rescaled_img = mh.stretch(clipped_img)
                haralick_values = mh.features.haralick(
                    img, ignore_zeros=False, return_mean=True
                )
                if not isinstance(haralick_values, np.ndarray):
                    # NOTE: setting `ignore_zeros` to True creates problems for some
                    # objects, when all values of the adjacency matrices are zeros
                    haralick_values = np.empty((len(self.names), ), dtype=float)
                    haralick_values[:] = np.NAN
                values.extend(haralick_values)
            features.append(values)
        return pd.DataFrame(features, columns=self.names, index=self.object_ids)


class PointPattern(Features):

    '''Class for performing a point pattern analysis.'''

    def __init__(self, label_image, parent_label_image):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image encoding objects (connected pixel components)
            for which point pattern should be assessed
        parent_label_image: numpy.ndarray[numpy.int32]
            labeled image encoding parent objects (connected pixel components)
            relative to which point patterns should be assessed
        '''
        super(PointPattern, self).__init__(label_image)
        self.parent_label_image = parent_label_image
        if self.label_image.shape != self.parent_label_image.shape:
            raise ValueError(
                'Image "parent_label_image" must have same dimensions as '
                '"label_image".'
            )

    def get_points_object_label_image(self, parent_object_id):
        '''Extracts the bounding box for a given parent object from
        :attr:`label_image <jtlib.features.PointPattern.label_image>`.

        Parameters
        ----------
        parant_object_id: int
            ID of object in
            :attr:`parent_label_image <jtlib.features.PointPattern.parent_label_image>`

        Returns
        -------
        numpy.ndarray[numpy.int32]
            label image for all objects falling within the bounding box of the
            given parent object

        '''
        bbox = self._parent_bboxes[parent_object_id]
        parent_img = self.get_parent_object_mask_image(parent_object_id)
        img = utils.extract_bbox(self.label_image, bbox=bbox, pad=1)
        img[~parent_img] = 0
        return img

    def get_parent_object_mask_image(self, parent_object_id):
        '''Extracts the bounding box for a given parent object from
        :attr:`parent_label_image <jtlib.features.PointPattern.parent_label_image>`.

        Returns
        -------
        numpy.ndarray[bool]
            mask image for given object
        '''
        bbox = self._parent_bboxes[parent_object_id]
        img = utils.extract_bbox(self.parent_label_image, bbox=bbox, pad=1)
        return img == parent_object_id

    @cached_property
    def _parent_bboxes(self):
        '''List[numpy.ndarray]: bounding boxes for each object in
        :attr:`parent_label_image <jtlib.features.PointPattern.parent_label_image>`.
        '''
        return mh.labeled.bbox(self.parent_label_image)

    @property
    def parent_object_ids(self):
        '''List[int]: IDs of objects in
        :attr:`parent_label_image <jtlib.features.PointPattern.parent_label_image>`
        '''
        return np.unique(self.parent_label_image)[1:].tolist()

    @property
    def _feature_names(self):
        return [
            'absolute-distance-to-border',
            'relative-distance-to-border',
            'absolute-distance-to-nearest-neighbor',
            'relative-distance-to-nearest-neighbor',
            'mean-absolute-distance-to-neighbors',
            'std-absolute-distance-to-neighbors',
            'mean-relative-distance-to-neighbors',
            'std-relative-distance-to-neighbors',
        ]

    def extract(self):
        '''Extracts point pattern features.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in
            :attr:`label_image <jtlib.features.PointPattern.label_image>`
        '''

        logger.info('extract point pattern features')
        features = dict()
        for obj in self.parent_object_ids:
            parent_obj_img = self.get_parent_object_mask_image(obj)
            points_img = self.get_points_object_label_image(obj)
            point_ids = np.unique(points_img)[1:]
            mh.labeled.relabel(points_img, inplace=True)

            size = np.sum(parent_obj_img)
            abs_border_dist_img = mh.distance(parent_obj_img).astype(float)
            rel_border_dist_img = abs_border_dist_img / size
            centroids = mh.center_of_mass(points_img, labels=points_img)
            centroids = centroids[1:, :].astype(int)
            abs_distance_matrix = squareform(pdist(centroids))
            rel_distance_matrix = abs_distance_matrix / size

            indexer = np.arange(centroids.shape[0])
            if len(indexer) == 0:
                continue
            if len(indexer) == 1:
                y, x = centroids[0, :]
                values = [
                    abs_border_dist_img[y, x],
                    rel_border_dist_img[y, x],
                    np.nan,
                    np.nan,
                    np.nan,
                    np.nan,
                    np.nan,
                    np.nan
                ]
                features[point_ids[0]] = values
                continue
            for i, (y, x) in enumerate(centroids):
                idx = indexer != i
                values = [
                    abs_border_dist_img[y, x],
                    rel_border_dist_img[y, x],
                    np.nanmin(abs_distance_matrix[i, idx]),
                    np.nanmin(rel_distance_matrix[i, idx]),
                    np.nanmean(abs_distance_matrix[i, idx]),
                    np.nanstd(abs_distance_matrix[i, idx]),
                    np.nanmean(rel_distance_matrix[i, idx]),
                    np.nanstd(rel_distance_matrix[i, idx]),
                ]
                features[point_ids[i]] = values

        ids = features.keys()
        values = list()
        nans = [np.nan for _ in range(len(self.names))]
        for i in self.object_ids:
            if i not in ids:
                logger.warn('values missing for object #%d', i)
                features[i] = nans
            values.append(features[i])
        return pd.DataFrame(values, columns=self.names, index=self.object_ids)



def create_feature_image(feature_values, label_image):
    '''Creates an image, where pixels belonging to an object
    (connected component) encode a given feature value.

    Parameters
    ----------
    feature_values: numpy.ndarray[numpy.float64]
        vector of feature values of length *n*, where *n* is the
        number of labeled connected component in `label_image`
    label_image: numpy.ndarray[numpy.int32]
        labeled image with *n* unique label values

    Returns
    -------
    numpy.ndarray[numpy.float64]
        feature image
    '''
    object_ids = np.unique(label_image)[1:]
    if len(object_ids) == 0:
        return np.zeros(label_image.shape, np.float64)
    if len(object_ids) != len(feature_values):
        raise ValueError(
            'Number of feature values doesn\'t match number of objects in the '
            'labeled image.'
        )
    preprented_feature_values = np.insert(feature_values, 0, 0)
    return preprented_feature_values[label_image].astype(np.float64)
