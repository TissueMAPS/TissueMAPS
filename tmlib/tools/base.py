# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Base classes for data analysis tools.'''
import re
import logging
import inspect
import importlib
import simplejson
import numpy as np
import pandas as pd
import collections
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import FLOAT

from tmlib import cfg
import tmlib.models as tm
from tmlib.config import DEFAULT_LIB, IMPLEMENTED_LIBS
from tmlib.utils import (
    same_docstring_as, autocreate_directory_property, assert_type
)

logger = logging.getLogger(__name__)

_register = {}


class _ToolMeta(ABCMeta):

    '''Meta class for :class:`Tool <tmlib.tools.base.Tool>`.'''

    def __init__(cls, cls_name, cls_bases, cls_args):

        def is_abstract(cls):
            is_abstract = False
            if '__abstract__' in vars(cls):
                if getattr(cls, '__abstract__'):
                    is_abstract = True
            return is_abstract

        if not is_abstract(cls):
            required_attrs = {'__icon__', '__description__'}
            for attr in required_attrs:
                if not hasattr(cls, attr):
                    raise AttributeError(
                        'Tool class "%s" must implement attribute "%s".' % (
                            cls_name, attr
                        )
                    )
            logger.debug('registering tool %s', cls.__name__)
            _register[cls_name] = cls
        return super(_ToolMeta, cls).__init__(cls_name, cls_bases, cls_args)

    def __call__(cls, *args, **kwargs):
        return super(_ToolMeta, cls).__call__(*args, **kwargs)


class Tool(object):

    '''Abstract base class for data analysis tools.

    Tools use the
    `Pandas DataFrame <http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html>`_ data container.
    This is compatible with standard machine learning libries,
    such as `Scikit-Learn <http://scikit-learn.org/stable/>`_
    `Caffe <http://caffe.berkeleyvision.org/>`_ or `Keras <https://keras.io/>`_.
    '''

    __metaclass__ = _ToolMeta

    __abstract__ = True

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the experiment for which the tool request is made
        '''
        self.experiment_id = experiment_id

    def load_feature_values(self, mapobject_type_name, feature_names):
        '''Selects all values for the each given features and
        mapobject types.

        Parameters
        ----------
        mapobject_type_name: str
            name of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        feature_names: List[str]
            name of each selected
            :class:`Feature <tmlib.models.feature.Feature>`

        Returns
        -------
        pandas.DataFrame
            dataframe where columns are features and rows are mapobjects
            indexable by their ID
        '''
        logger.info(
            'load values for objects of type "%s" and features: "%s"',
            mapobject_type_name, '", "'.join(feature_names)
        )
        # FIXME: Use ExperimentSession
        with tm.utils.ExperimentConnection(self.experiment_id) as conn:
            conn.execute('''
                SELECT t.id AS mapobject_type_id, f.id AS feature_id, f.name
                FROM features AS f
                JOIN mapobject_types AS t ON t.id = f.mapobject_type_id
                WHERE f.name = ANY(%(feature_names)s)
                AND t.name = %(mapobject_type_name)s;
            ''', {
                'feature_names': feature_names,
                'mapobject_type_name': mapobject_type_name
            })
            records = conn.fetchall()
            mapobject_type_id = records[0].mapobject_type_id
            feature_map = {str(r.feature_id): r.name for r in records}
            conn.execute('''
                SELECT
                    v.mapobject_id, v.tpoint,
                    slice(v.values, %(feature_ids)s) AS values
                FROM feature_values AS v
                JOIN mapobjects AS m
                ON m.id = v.mapobject_id AND m.partition_key = v.partition_key
                WHERE m.mapobject_type_id = %(mapobject_type_id)s
            ''', {
                'feature_ids': feature_map.keys(),
                'mapobject_type_id': mapobject_type_id
            })
            records = conn.fetchall()
            values = list()
            index = list()
            for r in records:
                values.append(r.values)
                index.append((r.mapobject_id, r.tpoint))
            index = pd.MultiIndex.from_tuples(
                index, names=['mapobject_id', 'tpoint']
            )

        # TODO: This probably creates a copy in memory. Can we avoid this?
        df = pd.DataFrame(values, index=index).astype(float)
        column_map = {i: name for i, name in feature_map.iteritems()}
        df.rename(columns=column_map, inplace=True)

        null_indices = self.get_features_with_null_values(df)
        for name, count in null_indices:
            if count > 0:
                logger.warn('feature "%s" contains %d null values', name, count)

        return df

    def calculate_extrema(self, mapobject_type_name, feature_name):
        '''Calcultes the minimum and maximum over values of a given
        feature and mapobject type.

        Parameters
        ----------
        mapobject_type_name: str
            name of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        feature_names: List[str]
            name of each selected
            :class:`Feature <tmlib.models.feature.Feature>`

        Returns
        -------
        Tuple[float]
            min and max
        '''
        logger.info(
            'calculate min/max for objects of type "%s" and feature "%s"',
            mapobject_type_name, feature_name
        )
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_type = session.query(tm.MapobjectType.id).\
                filter_by(name=mapobject_type_name).\
                one()
            feature = session.query(tm.Feature.id).\
                filter_by(
                    name=feature_name, mapobject_type_id=mapobject_type.id
                ).\
                one()

            lower, upper = session.query(
                    func.min(
                        tm.FeatureValues.values[str(feature.id)].cast(FLOAT)
                    ),
                    func.max(
                        tm.FeatureValues.values[str(feature.id)].cast(FLOAT)
                    )
                ).\
                join(tm.Mapobject).\
                filter(
                    tm.Mapobject.mapobject_type_id == mapobject_type.id,
                    tm.FeatureValues.values[str(feature.id)] != 'nan'
                ).\
                one()

        return (lower, upper)

    def get_features_with_null_values(self, feature_data):
        '''Gets names of features with NULL values.

        Parameters
        ----------
        feature_data: pandas.DataFrame
            data frame where columns are feature names and rows and objects

        Returns
        -------
        Tuple[Union[str, int]]
            name of the feature and the number of objects with NULL values
        '''
        null_indices = list()
        for name, values in feature_data.isnull().iteritems():
            null_indices.append((name, np.sum(values)))
        return null_indices

    def save_result_values(self, mapobject_type_name, result_id, data):
        '''Saves the generated label values.

        Parameters
        ----------
        mapobject_type_name: str
            name of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        result_id: int
            ID of a registerd
            :class:`ToolResult <tmlib.models.result.ToolResult>`
        data: pandas.Series
            series with multi-level index for "mapobject_id" and "tpoint"

        See also
        --------
        :class:`tmlib.models.result.LabelValues`
        '''
        logger.info('save label values for result %d', result_id)
        with tm.utils.ExperimentConnection(self.experiment_id) as connection:
            connection.execute('''
                SELECT id FROM mapobject_types
                WHERE name = %(mapobject_type_name)s
            ''', {
                'mapobject_type_name': mapobject_type_name
            })
            results = connection.fetchall()
            mapobject_type_id = results[0][0]
            connection.execute('''
                SELECT partition_key, array_agg(id) AS mapobject_ids
                FROM mapobjects AS m
                WHERE m.mapobject_type_id = %(mapobject_type_id)s
                GROUP BY partition_key
            ''', {
                'mapobject_type_id': mapobject_type_id
            })
            records = connection.fetchall()

            # NOTE: Grouping mapobject IDs per partition_key would allow us
            # to target individual shards of the label_values table directly
            # on the worker nodes, which would give us full SQL support,
            # including multi-row statements and transactions.
            # This would probably give a hugh performance benefit for inserting
            # or updating values.
            for tpoint in data.index.levels[1]:
                for partition_key, mapobject_ids in records:
                    logger.debug(
                        'upsert label values for partition %d', partition_key
                    )
                    for mapobject_id in mapobject_ids:
                        value = np.round(data.ix[(mapobject_id, tpoint)], 6)
                        connection.execute('''
                            INSERT INTO label_values AS v (
                                partition_key, mapobject_id, values, tpoint
                            )
                            VALUES (
                                %(partition_key)s, %(mapobject_id)s,
                                %(values)s, %(tpoint)s
                            )
                            ON CONFLICT ON CONSTRAINT label_values_pkey
                            DO UPDATE
                            SET values = v.values || %(values)s
                            WHERE v.mapobject_id = %(mapobject_id)s
                            AND v.partition_key = %(partition_key)s
                            AND v.tpoint = %(tpoint)s;
                        ''', {
                            'values': {str(result_id): str(value)},
                            'mapobject_id': mapobject_id,
                            'partition_key': partition_key,
                            'tpoint': tpoint
                        })

    def register_result(self, submission_id, mapobject_type_name,
            result_type, **result_attributes):
        '''Registers a result for the given tool request.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        mapobject_type_name: str
            name of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        result_type: str
            name of a class derived from
            :class:`ToolResult <tmlib.models.result.ToolResult>`
        **result_attributes: dict, optional
            result-specific attributes as key-value value pairs
            that get parsed to the constructor of the implemented `result_type`

        Returns
        -------
        int
            ID of the tool result
        '''
        logger.info('register result')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_type = session.query(tm.MapobjectType.id).\
                filter_by(name=mapobject_type_name).\
                one()
            try:
                module_name = 'tmlib.models.result'
                module = importlib.import_module(module_name)
                cls = getattr(module, result_type)
            except ImportError:
                raise ImportError(
                    'Ups this module should exist: %s' % module_name
                )
            except AttributeError:
                raise ValueError(
                    '"%s" is not a valid result type.' % result_type
                )
            required_args = inspect.getargspec(cls.__init__).args[1:]
            provided_args = {
                'submission_id', 'tool_name', 'mapobject_type_id', 'type'
            }
            for arg in required_args:
                if arg not in result_attributes and arg not in provided_args:
                    raise ValueError(
                        'Argument "%s" is required for result of type "%s".'
                        % (arg, result_type)
                    )

            # A result might already exist, for example when debugging
            # or when the job got canceled.
            result = session.query(tm.ToolResult).\
                filter_by(submission_id=submission_id).\
                one_or_none()
            if result is None:
                result = tm.ToolResult(
                    submission_id, self.__class__.__name__, mapobject_type.id,
                    type=result_type, **result_attributes
                )
                session.add(result)
                session.flush()
            return result.id

    @abstractmethod
    def process_request(self, submission_id, payload):
        '''Processes a tool request sent by the client.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        payload: dict
            an arbitrary mapping provided by the client that describes the job

        '''
        pass


class Classifier(Tool):

    '''Abstract base class for classification tools.'''

    __abstract__ = True

    @same_docstring_as(Tool.__init__)
    def __init__(self, experiment_id):
        super(Classifier, self).__init__(experiment_id)

    def label(self, feature_data, labeled_mapobjects):
        '''Adds labels to `feature_data` for supervised classification.

        Parameters
        ----------
        feature_data: pandas.DataFrame
            data frame where columns are features and rows are mapobjects
            as generated by
            :meth:`Classifier.load <tmlib.tools.base.Classfier.load>`
        labeled_mapobjects: Tuple[int]
            ID and assigned label for each selected
            :class:`Mapobject <tmlib.models.mapobject.Mapobject>`

        Returns
        -------
        pandas.DataFrame
            subset of `feature_data` for selected mapobjects with additional
            "label" column
        '''
        labeled_mapobjects = dict(labeled_mapobjects)
        ids = labeled_mapobjects.keys()
        labels = labeled_mapobjects.values()
        labeled_feature_data = feature_data[feature_data.index.isin(ids)].copy()
        labeled_feature_data['label'] = labels
        return labeled_feature_data

    def classify_supervised(self, feature_data, labels, method, n_fold_cv):
        '''Trains a classifier for labeled mapobjects based on
        `labeled_feature_data` and predicts labels for all mapobjects in
        `unlabeled_feature_data`.

        Parameters
        ----------
        feature_data: pandas.DataFrame
            feature values that should be used for classification
        labels: Dict[int, int]
            mapping of :class:`Mapobject <tmlib.models.mapobject.Mapobject>`
            ID to assigned label
        method: str
            method to use for classification
        n_fold_cv: int
            number of crossvalidation iterations (*n*-fold)

        Returns
        -------
        pandas.Series
            predicted labels for each entry in `feature_data`
        '''
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import SGDClassifier
        from sklearn.svm import SVC
        from sklearn.preprocessing import RobustScaler
        from sklearn.model_selection import GridSearchCV, KFold

        logger.info('perform classification using "%s" method', method)
        models = {
            'randomforest': {
                # NOTE: RF could be parallelized.
                'cls': RandomForestClassifier(n_jobs=1),
                # No scaling required for decision trees.
                'scaler': None,
                'search_space': {
                    # Number of trees.
                    'n_estimators': [3, 6, 12, 24],
                    # Number of leafs in the tree.
                    'max_depth': [3, 6, 12, None],
                    'min_samples_split': [2, 4, 8],
                    # TODO: this should rather be a user defined parameter
                    'class_weight': ['balanced', None]
                },
            },
            'svm': {
                'cls': SVC(cache_size=500, decision_function_shape='ovr'),
                # Scale to zero mean and unit variance
                'scaler': RobustScaler(quantile_range=(1.0, 99.0), copy=False),
                # Search optimal regularization parameters to control
                # model complexity.
                'search_space': {
                    'kernel': ['linear', 'rbf'],
                    'C': np.logspace(-5, 15, 10, base=2),
                    'gamma': np.logspace(-15, -3, 10, base=2)
                }
            },
            'logisticregression': {
                'cls': SGDClassifier(
                    loss='log', fit_intercept=False,
                    n_jobs=1, penalty='elasticnet'
                ),
                # Scale to zero mean and unit variance
                'scaler': RobustScaler(quantile_range=(1.0, 99.0), copy=False),
                # Search optimal regularization parameters to control
                # model complexity.
                'search_space': {
                    'alpha': np.logspace(-6, -1, 10),
                    'l1_ratio': np.linspace(0, 1, 10)
                }
            }
        }

        # TODO: We may want to include tpoint into labels mapping.
        train_index = feature_data.index.get_level_values('mapobject_id').isin(
            labels.keys()
        )
        X_train = feature_data.iloc[train_index]
        y = list()
        for i in X_train.index.get_level_values('mapobject_id'):
            y.append(labels[i])
        X_test = feature_data
        scaler = models[method]['scaler']
        # TODO: identify NaN and infinite values
        if scaler:
            # Fit scaler on the entire dataset.
            scaler.fit(feature_data)
            X_train = scaler.transform(X_train)
            X_test = scaler.transform(X_test)
        clf = models[method]['cls']
        folds = KFold(n_splits=n_fold_cv)
        # TODO: Second, finer grid search
        gs = GridSearchCV(clf, models[method]['search_space'], cv=folds)
        logger.info('fit model')
        gs.fit(X_train, y)
        logger.info('predict labels')
        predictions = gs.predict(X_test)
        return pd.Series(predictions, index=feature_data.index)

    def classify_unsupervised(self, feature_data, k, method):
        '''Groups mapobjects based on `data` into `k` classes.

        Parameters
        ----------
        feature_data: pandas.DataFrame
            feature values
        k: int
            number of classes
        method: str
            model to use for clustering

        Returns
        -------
        pandas.Series
            label (class membership) for each entry in `feature_data`
        '''
        from sklearn.cluster import KMeans
        models = {
            'kmeans': KMeans
        }
        logger.info('perform clustering using "%s" method', method)
        clf = models[method](n_clusters=k)
        logger.info('fit model')
        clf.fit(feature_data)
        logger.info('predict labels')
        labels = clf.labels_
        return pd.Series(labels, index=feature_data.index)
