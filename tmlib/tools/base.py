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
import logging
import inspect
import importlib
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

    '''Meta class for :class:`tmlib.tools.base.Tool`.'''

    def __init__(cls, cls_name, cls_bases, cls_args):
        if hasattr(cls, '__libs__'):
            if not isinstance(cls.__libs__, dict):
                raise TypeError(
                    'Attibute "__libs__" of class "%s" must have type dict.' %
                    cls_name
                )
            if DEFAULT_LIB not in cls.__libs__:
                raise KeyError(
                    'Attibute "__libs__" of class "%s" must have key "%s"' % (
                        cls_name, DEFAULT_LIB
                    )
                )
            for lib in cls.__libs__:
                if lib not in IMPLEMENTED_LIBS:
                    raise KeyError(
                        'Key "%s" in "__libs__" of class "%s" is not an '
                        'implemented library! Implemented are: "%s"' % (
                            lib, cls_name, '", "'.join(IMPLEMENTED_LIBS)
                        )
                    )
        register = True
        if '__abstract__' in vars(cls):
            if getattr(cls, '__abstract__'):
                register = False
        if register:
            required_attrs = {'__icon__', '__description__'}
            for attr in required_attrs:
                if not hasattr(cls, attr):
                    raise AttributeError(
                        'Tool class "%s" must implement attribute "%s".' % (
                            cls_name, attr
                        )
                    )
            _register[cls_name] = cls
        return super(_ToolMeta, cls).__init__(cls_name, cls_bases, cls_args)

    def __call__(cls, *args, **kwargs):
        mixin_mapping = collections.defaultdict(list)
        classes = [cls]
        classes += inspect.getmro(cls)
        for c in classes:
            if hasattr(c, '__libs__'):
                for lib, mixin_cls in c.__libs__.iteritems():
                    mixin_mapping[lib].append(mixin_cls)
        for mixin_cls in mixin_mapping.get(cfg.tool_library):
            if mixin_cls not in cls.__bases__:
                cls.__bases__ += (mixin_cls,)
        return super(_ToolMeta, cls).__call__(*args, **kwargs)


class ToolInterface(object):

    '''Abstract base class for tool library interfaces.'''

    __metaclass__ = ABCMeta

    @abstractmethod
    def load_data(self):
        pass

    @abstractmethod
    def load_feature_values(self, mapobject_type_name, feature_name):
        pass

    @abstractmethod
    def save_label_values(self, result_id, data):
        pass

    @abstractmethod
    def calculate_extrema(self, data, column):
        pass

    @abstractmethod
    def calculate_unique(self, data, column):
        pass


class ToolSparkInterface(ToolInterface):

    '''Tool interface for the `Spark <http://spark.apache.org/>`_ library.

    The interface uses the
    `Spark DataFrame <http://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.DataFrame>`_
    data container together with the
    `Spark MLlib <http://spark.apache.org/docs/latest/api/python/pyspark.ml.html>`
    machine learning library.
    '''

    def _create_spark_session(self, tool_name):
        '''Creates a Spark Session.'''
        from pyspark.sql import SparkSession
        session = SparkSession.builder.\
            master(cfg.spark_master).\
            appName(tool_name).\
            getOrCreate()
        session.sparkContext.setLogLevel('WARN')
        return session

    def _read_table(self, table, n_partitions, lower_bound, upper_bound):
        '''Reads a SQL table for use with Apache Spark.

        Parameters
        ----------
        table: str
            name of the SQL table or aliased SQL query
        n_partitions: int
            number of partitions for parallel processing
        lower_bound: int
            value of lowest ID in `table`
        upper_bound: int
            value of highest ID in `table`

        Returns
        -------
        pyspark.sql.DataFrame

        Note
        ----
        Caches the :class:`pyspark.sql.DataFrame` to speed up computations.

        '''
        url = cfg.db_uri_spark.replace(
            'tissuemaps', 'tissuemaps_experiment_%s' % self.experiment_id
        )
        df = self.spark.read.jdbc(
            url=url, table=table, column='id',
            lowerBound=lower_bound, upperBound=upper_bound,
            numPartitions=n_partitions,
        )
        return df.cache()

    @staticmethod
    def _build_feature_values_query(mapobject_type_name, feature_name):
        # We run the actual query in SQL, since this performs way better
        # compared to loading the table and then filtering it via Spark
        # NOTE: the alias is required for compatibility with DataFrameReader
        return '''
            (SELECT v.value, v.mapobject_id, v.id FROM feature_values AS v
            JOIN features AS f ON f.id=v.feature_id
            JOIN mapobject_types AS t ON t.id=f.mapobject_type_id
            WHERE f.name=\'{feature_name}\'
            AND t.name=\'{mapobject_type_name}\'
            ) AS t
        '''.format(
            mapobject_type_name=mapobject_type_name.replace(';', ''),
            feature_name=feature_name.replace(';', '')
        )

    def load_feature_values(self, mapobject_type_name, feature_name):
        '''Selects all values from table "feature_values" for mapobjects of
        a given :class:`tmlib.models.MapbojectType` and
        :class:`tmlib.models.Feature`.

        Parameters
        ----------
        mapobject_type_name: str
            name of the selected mapobject type
        feature_name: str
            name of a selected feature

        Returns
        -------
        pyspark.sql.DataFrame
            data frame with columns "mapobject_id" and "value" and
            a row for each mapobject
        '''
        query = self._build_feature_values_query(
            mapobject_type_name, feature_name
        )
        lower, upper = self._determine_bounds(mapobject_type_name, feature_name)
        return self._read_table(
            table=query, n_partitions=100, lower_bound=lower, upper_bound=upper,
        )

    def save_label_values(self, result_id, data):
        '''Saves the generated label values in the corresponding database table.

        Parameters
        ----------
        result_id: int
            ID of corresponding tool result
        data: pyspark.sql.DataFrame
            data frame with columns "label" and "mapobject_id"

        See also
        --------
        :class:`tmlib.models.feature.LabelValue`
        '''
        import pyspark.sql.functions as sp
        url = cfg.db_uri_spark.replace(
            'tissuemaps', 'tissuemaps_experiment_%s' % self.experiment_id
        )
        table = tm.LabelLayerValue.__table__.name
        formatted_data = data.select(data.label.alias('value'))
        formatted_data = data.withColumn('tool_result_id', sp.lit(result_id))
        formatted_data.write.jdbc(url=url, table=table, mode='append')

    def calculate_extrema(self, data, column):
        '''Calculates the minimum and maximum of values in `column`.

        Parameters
        ----------
        data: pyspark.sql.DataFrame
            dataframe with `column`
        column: str
            name of column in `data`

        Returns
        -------
        Tuple[float]
            min and max
        '''
        import pyspark.sql.functions as sp
        stats = data.select(sp.min(column), sp.max(column)).collect()
        lower = stats[0][0]
        upper = stats[0][1]
        return (lower, upper)


class ToolPandasInterface(ToolInterface):

    '''Tool interface for the `Pandas <http://pandas.pydata.org/>`_ library.

    The interface uses the
    `Pandas DataFrame <http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html>`_
    data container together with the
    `Scikit-Learn <http://scikit-learn.org/stable/>`_ machine learning library.
    It can also be used with other machine learning libraries, such as
    `Caffe <http://caffe.berkeleyvision.org/>`_ or `Keras <https://keras.io/>`_.
    '''

    def load_feature_values(self, mapobject_type_name, feature_name):
        '''Selects all values from table "feature_values" for mapobjects of
        a given :class:`tmlib.models.MapbojectType` and
        :class:`tmlib.models.Feature`.

        Parameters
        ----------
        mapobject_type_name: str
            name of the selected mapobject type
        feature_name: str
            name of a selected feature

        Returns
        -------
        pandas.DataFrame
            data frame with columns "mapobject_id" and "value" and
            a row for each mapobject
        '''
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            feature_values = session.query(
                    tm.FeatureValue.mapobject_id,
                    tm.FeatureValue.value
                ).\
                join(tm.Feature).\
                join(tm.MapobjectType).\
                filter(
                    tm.Feature.name == feature_name,
                    tm.MapobjectType.name == mapobject_type_name
                ).\
                all()
        return pd.DataFrame(
            feature_values, columns=['mapobject_id', 'value']
        )

    def save_label_values(self, result_id, data):
        '''Saves the generated label values in the corresponding database table.

        Parameters
        ----------
        result_id: int
            ID of corresponding tool result
        data: pandas.DataFrame
            data frame with columns "label" and "mapobject_id"

        See also
        --------
        :class:`tmlib.models.feature.LabelValue`
        '''
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            label_mappings = [
                {
                    'value': row.label,
                    'mapobject_id': row.mapobject_id,
                    'tool_result_id': result_id
                }
                for index, row in data.iterrows()
            ]
            session.bulk_insert_mappings(tm.LabelValue, label_mappings)

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



class Tool(object):

    '''Abstract base class for a data analysis `tool`.

    Derived classes delegate the actual processing to either the
    `pandas` or the `spark` library interface. Both libraries use a data
    container called "DataFrame" and have very similar interfaces. Note,
    however, that spark code gets evaluated lazily.

    Common methods required by both libraries should be implemented directly
    in the derived class. Library-specific processing methods should
    be implemented in separate mixin classes. These library-specific mixins
    must be provided to the derived class via the ``__libs__`` attribute
    (in form of a mapping library name -> mixin class).
    The appropriate library interface will be chosen automatically based on
    configuration of :attr:`tmlib.config.tool_library` and injected upon
    instantiation of the derived class. This provides tools with a uniform
    interface independent of the specificities of different library backends.

    By default, the `pandas` library will be used and you don't need to
    have `Spark <http://spark.apache.org/>`_ installed.
    When setting :attr:`tmlib.config.LibraryConfig.tool_library` to ``spark``,
    the `spark` library will be used instead. The required
    `Spark Session <https://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.SparkSession>`_
    (the main entry point for `Spark` functionality) gets automatically created
    and made available to instances of derived classes as ``spark`` attribute.

    On small datasets, `pyspark` is an overkill and running analysis in memory
    using `pandas` will be faster in most cases. However, `pyspark` pays off on
    large datasets, in particular in combination with a
    `Spark cluster <http://spark.apache.org/docs/latest/cluster-overview.html>`_.
    `TissueMAPS` supports running `spark` tool requests in a distributed manner
    on `YARN <http://spark.apache.org/docs/latest/running-on-yarn.html>`_.
    '''

    __metaclass__ = _ToolMeta

    __abstract__ = True

    __libs__ = {'spark': ToolSparkInterface, 'pandas': ToolPandasInterface}

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the experiment for which the tool request is made
        '''
        self.experiment_id = experiment_id
        if cfg.tool_library == 'spark':
            self.spark = self._create_spark_session(self.__class__.__name__)

    def initialize_result(self, submission_id, mapobject_type_name,
            layer_type, **layer_args):
        '''Initializes a result for the given tool request.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        mapobject_type_name: str
            name of the selected mapobject type
        layer_type: str
            name of subclass of :class:`tmlib.models.layer.LabelLayer`
        **layer_args: dict, optional
            `layer_type`-specific attributes as key-value value pairs
            that get parsed to the constructor of the corresponding subclass
            of :class:`tmlib.models.layer.LabelLayer`

        Returns
        -------
        int
            ID of the tool result
        '''
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_type = session.query(tm.MapobjectType.id).\
                filter_by(name=mapobject_type_name).\
                one()
            result = tm.ToolResult(
                submission_id, self.__class__.__name__, mapobject_type.id
            )
            session.add(result)
            session.flush()
            try:
                module_name = 'tmlib.models.layer'
                module = importlib.import_module(module_name)
                cls = getattr(module, layer_type)
            except ImportError:
                raise ImportError(
                    'Ups this module should exist: %s' % module_name
                )
            except AttributeError:
                raise ValueError(
                    '"%s" is not a valid LabelLayer type.' % label_type
                )
            required_args = inspect.getargspec(cls.__init__).args[1:]
            provided_args = {'tool_result_id', 'type'}
            for arg in required_args:
                if arg not in layer_args and arg not in provided_args:
                    raise ValueError(
                        'Argument "%s" is required for LabelLayer of type "%s".'
                        % (arg, layer_type)
                    )
            layer = tm.LabelLayer(result.id, type=layer_type, **layer_args)
            session.add(layer)
            return result.id

    def _determine_bounds(self, mapobject_type_name, feature_name):
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            query = session.query(tm.FeatureValue.id).\
                join(tm.Feature).\
                join(tm.MapobjectType).\
                filter(
                    tm.Feature.name == feature_name,
                    tm.MapobjectType.name == mapobject_type_name
                )
            lower = query.order_by(tm.FeatureValue.id).limit(1).one()
            upper = query.order_by(tm.FeatureValue.id.desc()).limit(1).one()
            return (lower.id, upper.id)

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


class ClassifierInterface(object):

    '''Abstract base class for classifier tool library interfaces.'''

    __metaclass__ = ABCMeta

    @abstractmethod
    def load_feature_values(self, mapobject_type_name, feature_names):
        pass

    @abstractmethod
    def label_feature_data(self, feature_data, labeled_mapobjects):
        pass

    @abstractmethod
    def classify_supervised(self, unlabeled_feature_data, labeled_feature_data,
            method):
        pass

    @abstractmethod
    def classify_unsupervised(self, feature_data, k, method):
        pass


class ClassifierSparkInterface(ClassifierInterface):

    def load_feature_values(self, mapobject_type_name, feature_names):
        '''Loads feature values from the database and brings the dataset into
        the format required by classifiers.

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
        pyspark.sql.DataFrame
            dataframe with a "features" column in form of a
            :class:`pyspark.mllib.linalg.DenseVector` as required by classifiers
            of the :mod:`pyspark.ml` package and a "mapobject_id" column
        '''
        from pyspark.ml.feature import VectorAssembler
        for i, name in enumerate(feature_names):
            df = ToolSparkInterface.load_feature_values(self,
                mapobject_type_name, name
            )
            if i == 0:
                data = df.select(
                    df.value.alias(name),
                    df.mapobject_id
                )
            else:
                df = df.select(
                    df.value.alias(name),
                    df.mapobject_id.alias('%s_mapobject_id' % name)
                )
                on = data['mapobject_id'] == df['%s_mapobject_id' % name]
                data = data.join(df, on, 'inner').drop('%s_mapobject_id' % name)

        assembler = VectorAssembler(
            inputCols=feature_names, outputCol='features'
        )
        return assembler.transform(data).select('features', 'mapobject_id')

    def calculate_unique(self, data, column):
        '''Calculates the set of unique values of `column`.

        Parameters
        ----------
        data: pyspark.sql.DataFrame
            dataframe with `column`
        column: str
            name of column in `data`

        Returns
        -------
        List[float]
            unique values
        '''
        import pyspark.sql.functions as sp
        stats = data.select(sp.collect_set(column)).collect()
        return stats[0][0]

    def label_feature_data(self, feature_data, labeled_mapobjects):
        '''Adds labels to `feature_data` for supervised classification.

        Parameters
        ----------
        feature_data: pyspark.sql.DataFrame
            data frame where columns are features and rows are mapobjects
        labeled_mapobjects: Tuple[int]
            ID and assigned label for each selected
            :class:`tmlib.models.mapobject.Mapobject`

        Returns
        -------
        pyspark.sql.DataFrame
            subset of `feature_data` for selected mapobjects with additional
            "label" column
        '''
        labels = spark.sqlc.createDataFrame(
            labeled_mapobjects, schema=['mapobject_id', 'label']
        )
        labeled_data = feature_data.join(
            labels, labels['mapobject_id'] == feature_data['mapobject_id']
        ).cache()
        return labeled_data

    def classify_supervised(self, unlabeled_feature_data, labeled_feature_data, method):
        '''Trains a classifier for labeled mapobjects based on
        `labeled_feature_data` and predicts labels for all mapobjects in
        `unlabeled_feature_data`.

        Parameters
        ----------
        unlabeled_feature_data: pyspark.sql.DataFrame
            mapobjects that should be classified
        labeled_feature_data: pyspark.sql.DataFrame
            data that should be used for training of the classifier
        method: str
            method to use for classification

        Returns
        -------
        List[Tuple[int, str]]
            ID and predicted label for each mapobject
        '''
        from pyspark.ml import Pipeline
        from pyspark.ml.feature import StringIndexer
        from pyspark.ml.feature import VectorAssembler
        from pyspark.ml.feature import VectorIndexer
        from pyspark.ml.feature import VectorAssembler, VectorIndexer, StringIndexer
        from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
        from pyspark.ml.classification import RandomForestClassifier
        from pyspark.ml.evaluation import MulticlassClassificationEvaluator

        logger.info('perform classification via Spark with "%s" method', method)
        feature_indexer = VectorIndexer(
                inputCol='features', outputCol='indexedFeatures',
                maxCategories=2
            ).\
            fit(labeled_feature_data)

        label_indexer = StringIndexer(
                inputCol='label', outputCol='indexedLabel'
            ).\
            fit(labeled_feature_data)

        label_df = label_indexer.transform(labeled_feature_data)
        label_mapping = {
            r.indexedLabel: r.label
            for r in label_df.select('label','indexedLabel').distinct().collect()
        }
        # TODO: How can this be achieved with IndexToString() when prediction
        # is done on unlabeled dataset?
        # label_converter = IndexToString(
        #     inputCol='prediction', outputCol='predictedLabel',
        #     labels=label_indexer.labels
        # )

        models = {
            'randomforest': RandomForestClassifier
        }
        grid_search_space = {
            'randomforest': {
                'maxDepth': [3, 5, 7],
                'numTrees': [10, 20, 30]
            }
        }

        clf = models[method](
            labelCol='indexedLabel', featuresCol='indexedFeatures'
        )
        grid = ParamGridBuilder()
        for k, v in grid_search_space.iteritems():
            grid.addGrid(getattr(clf, k), v)
        grid.build()

        pipeline = Pipeline(stages=[feature_indexer, label_indexer, clf])
        evaluator = MulticlassClassificationEvaluator(
            labelCol='indexedLabel', predictionCol='prediction',
            metricName='f1'
        )
        crossval = CrossValidator(
            estimator=pipeline, estimatorParamMaps=grid,
            evaluator=evaluator, numFolds=3
        )
        logger.info('fit model')
        model = crossval.fit(labeled_feature_data)
        predictions = model.transform(unlabeled_feature_data)
        logger.info('collect predicted labels')
        return predictions.\
            select( sp.col('prediction').alias('label'), 'mapobject_id')

    def classify_unsupervised(self, feature_data, k, method):
        '''Clusters mapobjects based on `feature_data` using the
        machine learning library.

        Parameters
        ----------
        feature_data: pyspark.sql.DataFrame
            feature values
        k: int
            number of classes
        method: str
            model to use for clustering

        Returns
        -------
        pyspark.sql.DataFrame
            data frame with additional column "predictions" with predicted label
            values for each mapobject
        '''
        from pyspark.ml.clustering import KMeans
        import pyspark.sql.functions as sp
        models = {
            'kmeans': KMeans
        }
        logger.info('perform clustering via Spark with "%s" method', method)
        clf = models[method](k=k, seed=1)
        logger.info('fit model')
        model = clf.fit(feature_data)
        return model.transform(feature_data).\
            select(sp.col('prediction').alias('label'), 'mapobject_id')


class ClassifierPandasInterface(ClassifierInterface):

    def load_feature_values(self, mapobject_type_name, feature_names):
        '''Loads feature values from the database and brings the dataset into
        the format required by classifiers.

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
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_type_id = session.query(tm.MapobjectType.id).\
                filter_by(name=mapobject_type_name).\
                one()
            feature_values = session.query(
                    tm.Feature.name,
                    tm.FeatureValue.mapobject_id,
                    tm.FeatureValue.value
                ).\
                join(tm.FeatureValue).\
                filter(
                    (tm.Feature.name.in_(feature_names)) &
                    (tm.Feature.mapobject_type_id == mapobject_type_id)).\
                all()
        feature_df_long = pd.DataFrame(feature_values)
        feature_df_long.columns = ['features', 'mapobject', 'value']
        return pd.pivot_table(
            feature_df_long, values='value', index='mapobject',
            columns='features'
        )

    def calculate_unique(self, data, column):
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
        return np.unique(data[column]).astype(float).tolist()

    def label_feature_data(self, feature_data, labeled_mapobjects):
        '''Adds labels to `feature_data` for supervised classification.

        Parameters
        ----------
        feature_data: pandas.DataFrame
            data frame where columns are features and rows are mapobjects
            as generated by
            :meth:`tmlib.tools.base.Classfier.load_feature_values`
        labeled_mapobjects: Tuple[int]
            ID and assigned label for each selected
            :class:`tmlib.models.mapobject.Mapobject`

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
            method):
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

        Returns
        -------
        List[Tuple[int, str]]
            ID and predicted label for each mapobject
        '''
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.grid_search import GridSearchCV
        from sklearn import cross_validation

        logger.info(
            'perform classification via Scikit-Learn with "%s" method', method
        )
        models = {
            'randomforest': RandomForestClassifier
        }
        grid_search_space = {
            'randomforest': {
                'max_depth': [3, 5, 7],
                'min_samples_split': [1, 3, 10],
                'min_samples_leaf': [1, 3, 10]
            }
        }
        n_samples = labeled_feature_data.shape[0]
        n_folds = min(n_samples / 2, 10)

        X = labeled_feature_data.drop('label', axis=1)
        y = labeled_feature_data.label
        clf = models[method]()
        folds = cross_validation.StratifiedKFold(y, n_folds=n_folds)
        gs = GridSearchCV(clf, grid_search_space[method], cv=folds)
        logger.info('fit model')
        gs.fit(X, y)
        logger.info('predict labels')
        predictions = pd.DataFrame(
            gs.predict(unlabeled_feature_data).astype(float), columns=['label']
        )
        predictions['mapobject_id'] = feature_data.index.astype(int)
        return predictions

    def classify_unsupervised(self, feature_data, k, method):
        '''Clusters mapobjects based on `feature_data` using the
        machine learning library.

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
            data frame with additional column "predictions" with predicted label
            values for each mapobject
        '''
        from sklearn.cluster import KMeans

        models = {
            'kmeans': KMeans
        }
        logger.info(
            'perform clustering via Scikit-Learn with "%s" method', method
        )
        clf = models[method](n_clusters=k)
        logger.info('fit model')
        clf.fit(feature_data)
        # Ensure that values are JSON serializable
        logger.info('predict labels')
        predictions = pd.DataFrame(
            clf.labels_.astype(float), columns=['label']
        )
        predictions['mapobject_id'] = feature_data.index.astype(int)
        return predictions


class Classifier(Tool):

    '''Abstract base class for classification tools.'''

    __abstract__ = True

    __libs__ = {
        'spark': ClassifierSparkInterface, 'pandas': ClassifierPandasInterface
    }

    @same_docstring_as(Tool.__init__)
    def __init__(self, experiment_id):
        super(Classifier, self).__init__(experiment_id)

