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
        if hasattr(cls, '__lib_bases__'):
            if not isinstance(cls.__lib_bases__, dict):
                raise TypeError(
                    'Attibute "__lib_bases__" of class "%s" must have type dict.'
                    % cls_name
                )
            if DEFAULT_LIB not in cls.__lib_bases__:
                raise KeyError(
                    'Attibute "__lib_bases__" of class "%s" must have key "%s"'
                    % (cls_name, DEFAULT_LIB)
                )
            for lib in cls.__lib_bases__:
                if lib not in IMPLEMENTED_LIBS:
                    raise KeyError(
                        'Key "%s" in "__lib_bases__" of class "%s" is not an '
                        'implemented library! Implemented are: "%s"' % (
                            lib, cls_name, '", "'.join(IMPLEMENTED_LIBS)
                        )
                    )

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
        lib = None
        mixin_mapping = list()
        classes = [cls]
        classes += inspect.getmro(cls)
        # Process in reversed order, such that derived classes are considered
        # first for determining availability of libraries.
        for c in reversed(classes):
            if hasattr(c, '__lib_bases__'):
                # In case the configured library is not available for the tool,
                # we use the default library (it's implementation is enforced,
                # see _ToolMeta.__init__). In case of Spark this is no problem,
                # since the environment can also execute "normal" Python code.
                if lib is None:
                    if cfg.tool_library not in c.__lib_bases__:
                        logger.warn(
                            'defaulting to library "%s" for tool "%s"',
                            DEFAULT_LIB, cls.__name__
                        )
                        lib = DEFAULT_LIB
                    else:
                        logger.debug(
                            'using library "%s" for tool "%s"',
                            cfg.tool_library, cls.__name__
                        )
                        lib = cfg.tool_library
        # Process bases first, such that susequent implementation override
        # correclty.
        for c in classes:
            if hasattr(c, '__lib_bases__'):
                mixin_mapping.append(c.__lib_bases__[lib])
        for mixin_cls in mixin_mapping:
            if mixin_cls not in cls.__bases__:
                logger.debug('adding mixin %r to bases of %r', mixin_cls, cls)
                cls.__bases__ += (mixin_cls,)
        return super(_ToolMeta, cls).__call__(*args, **kwargs)


class Tool(object):

    '''Abstract base class for a data analysis tool.

    The interface uses the
    `Pandas DataFrame <http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html>`_
    data container together with the
    `Scikit-Learn <http://scikit-learn.org/stable/>`_ machine learning library.
    It could in principle also be used with other machine learning libraries,
    such as `Caffe <http://caffe.berkeleyvision.org/>`_,
    `Keras <https://keras.io/>`_ or `TensorFlow <https://www.tensorflow.org/>`_.

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
        '''Selects all values for each given
        :class:`tmlib.models.Feature` and mapobjects with a given
        :class:`tmlib.models.MapobjectType`.

        Parameters
        ----------
        mapobject_type_name: str
            name of the selected mapobject type
            (:class:`tmlib.models.mapobject.MapobjectType`)
        feature_names: List[str]
            names of selected features
            (:class:`tmlib.models.feature.Feature`)

        Returns
        -------
        pandas.DataFrame
            dataframe where columns are features and rows are mapobjects
            indexable by `mapobject_id`
        '''
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
            feature_map = {r.feature_id: r.name for r in records}
            mapobject_type_id = records[0].mapobject_type_id
            sql = '''
                SELECT mapobject_id, tpoint'''
            for i in feature_map:
                sql += ', (values->%%(id_%d)s)::double precision AS value_%d' % (i, i)
            sql += '''
                FROM feature_values AS v
                JOIN mapobjects AS m ON m.id = v.mapobject_id
                WHERE m.mapobject_type_id = %(mapobject_type_id)s
            '''
            parameters = {'id_%d' % i: str(i) for i in feature_map}
            parameters['mapobject_type_id'] = mapobject_type_id
            conn.execute(sql, parameters)
            feature_values = conn.fetchall()
        df = pd.DataFrame(feature_values)
        df.set_index('mapobject_id', inplace=True)
        # NOTE: We map the column names here and not in the SQL expression to
        # avoid parsing feature names, which are provided by the user and
        # thus pose a potential security risk in form of SQL injection.
        column_map = {
            'value_%d' % i: name for i, name in feature_map.iteritems()
        }
        df.rename(columns=column_map, inplace=True)
        return df

    def save_result_values(self, result_id, data):
        '''Saves the computed label values.

        Parameters
        ----------
        result_id: int
            ID of a registered
            :class:`ToolResult <tmlib.models.result.ToolResult>`
        data: pandas.DataFrame
            data frame with columns "label", "tpoint" and "mapobject_id"

        See also
        --------
        :class:`tmlib.models.result.LabelValues`
        '''
        with tm.utils.ExperimentConnection(self.experiment_id) as conn:
            # TODO: Use "mapobject_id" and "tpoint" as index
            for index, row in data.iterrows():
                conn.execute('''
                    INSERT INTO label_values AS v (
                        mapobject_id, values, tpoint
                    )
                    VALUES (
                        %(mapobject_id)s, %(values)s, %(tpoint)s
                    )
                    ON CONFLICT
                    ON CONSTRAINT label_values_tpoint_mapobject_id_key
                    DO UPDATE
                    SET values = v.values || %(values)s
                    WHERE v.mapobject_id = %(mapobject_id)s
                    AND v.tpoint = %(tpoint)s;
                ''', {
                    'values': {str(result_id): row.label},
                    'mapobject_id': row.mapobject_id,
                    'tpoint': row.tpoint
                })

    def calculate_extrema(self, data, column):
        '''Calculates the minimum and maximum of values in `column`.

        Parameters
        ----------
        data: pandas.DataFrame
            dataframe with `column`
        column: str
            name of column in `data`

        Returns
        -------
        Tuple[float]
            min and max
        '''
        lower = np.min(data[column])
        upper = np.max(data[column])
        return (lower, upper)

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
            result = tm.ToolResult(
                submission_id, self.__class__.__name__, mapobject_type.id,
                type=result_type, **result_attributes
            )
            session.add(result)
            session.flush()
            return result.id

    def unique(self, data, column):
        '''Calculates the set of unique values for `column`.

        Parameters
        ----------
        data: pandas.DataFrame
            dataframe with `column`
        column: str
            name of column in `data`

        Returns
        -------
        List[float]
            unique values
        '''
        return np.unique(data[column]).tolist()

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

    def classify_supervised(self, unlabeled_feature_data, labeled_feature_data,
            method, n_fold_cv):
        '''Trains a classifier for labeled mapobjects based on
        `labeled_feature_data` and predicts labels for all mapobjects in
        `unlabeled_feature_data`.

        Parameters
        ----------
        unlabeled_feature_data: pandas.DataFrame
            mapobjects that should be classified
        labeled_feature_data: pandas.DataFrame
            data that should be used for training of the classifier
        method: str
            method to use for classification
        n_fold_cv: int
            number of crossvalidation iterations (*n*-fold)

        Returns
        -------
        pandas.DataFrame
            dataframe with columns "label" and "mapobject_id"
        '''
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.svm import SVC
        from sklearn.grid_search import GridSearchCV
        from sklearn import cross_validation

        logger.info('perform classification using "%s" method', method)
        models = {
            'randomforest': {
                'cls': RandomForestClassifier(),
                'scaler': None,
                'search_space': {
                    'max_depth': [3, 5, 7],
                    'min_samples_split': [1, 3, 10],
                    'min_samples_leaf': [1, 3, 10]
                },
            },
            'svm': {
                'cls': SVC(loss='l2', cache_size=500),
                'scaler': StandardScaler(),
                'search_space': {
                    'kernel': ['linear', 'rbf'],
                    'penalty': ['l1', 'l2'],
                    'C': np.logspace(-2, 10, 13),
                    'gamma': np.logspace(-9, 3, 13)
                }
            }
        }

        X_train = labeled_feature_data.drop('label', axis=1)
        if models[method]['scaler']:
            X_train = models[method]['scaler'].fit_transform(X_train)
        y = labeled_feature_data.label
        clf = models[method]['cls']
        folds = cross_validation.StratifiedKFold(y, n_folds=n_fold_cv)
        gs = GridSearchCV(clf, models[method]['search_space'], cv=folds)
        logger.info('fit model')
        gs.fit(X_train, y)
        logger.info('predict labels')
        X_test = unlabeled_feature_data
        if models[method]['scaler']:
            X_test = models[method]['scaler'].fit_transform(X_predict)
        labels = gs.predict(X_test)
        # TODO: return labels directly?
        predictions = pd.DataFrame(labels, columns=['label'])
        predictions['tpoint'] = unlabeled_feature_data['tpoint']
        predictions['mapobject_id'] = unlabeled_feature_data.index.astype(int)
        return predictions

    def classify_unsupervised(self, data, k, method):
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
        pandas.DataFrame
            data frame with additional columns "label" and "mapobject_id"
        '''
        from sklearn.cluster import KMeans
        models = {
            'kmeans': KMeans
        }
        logger.info('perform clustering using "%s" method', method)
        clf = models[method](n_clusters=k)
        logger.info('fit model')
        clf.fit(feature_data)
        # Ensure that values are JSON serializable
        logger.info('predict labels')
        labels = clf.labels_
        # TODO: return labels directly?
        predictions = pd.DataFrame(labels, columns=['label'])
        predictions['tpoint'] = unlabeled_feature_data['tpoint']
        predictions['mapobject_id'] = feature_data.index.astype(int)
        return predictions
