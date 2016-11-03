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
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty

from tmlib import cfg
import tmlib.models as tm
from tmlib.utils import (
    same_docstring_as, autocreate_directory_property, assert_type
)

logger = logging.getLogger(__name__)



class _ToolMeta(ABCMeta):

    '''Metaclass for creation of :class:`tmlib.tools.base.Tool`.'''

    def __init__(self, name, bases, d):
        if name == 'Tool':
            return
        required_attrs = {'__icon__', '__description__'}
        is_abstract = getattr(self, '__abstract__', False)
        for attr in required_attrs:
            if not hasattr(self, attr) and not is_abstract:
                raise AttributeError(
                    'Class "%s" is derived from base class "Tool" '
                    'and must implement attribute "%s".' % (name, attr)
                )


class Tool(object):

    '''Abstract base class for a data analysis `tool`.

    The class provides methods for loading and formatting data in the format
    required by the `scikit-learn <http://scikit-learn.org/stable/>`_ and
    `pyspark <http://spark.apache.org/docs/latest/api/python/index.html>`_
    machine learning libraries. Both libraries use a data container called
    "dataframe" and have a similar syntax. However, `pyspark` code is
    evaluated lazily and requires the creation of a `session`
    as an entry point to Spark functionality.
    By default, the `scikit-learn` library will be used and you don't need to
    have `Spark <http://spark.apache.org/>`_ installed to use the tools.
    When setting :attr:`tmlib.config.LibraryConfig.use_spark` to ``True``,
    `pyspark` will be used instead and the class will automatically
    generate the required
    `pyspark.SparkSession <https://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.SparkSession>`_
    instance and make it available to instances of derived classes via the
    :attr:`tmlib.tools.base.Tool.spark` atrribute.

    On small datasets, `pyspark` is an overkill and running analysis in memory
    via `scikit-learn` would be advised. However, `pyspark` can pay off on
    large datasets particularly when combined with a
    `Spark cluster <http://spark.apache.org/docs/latest/cluster-overview.html>`_.
    To this end, `TissueMAPS` supports running tool requests in `spark` mode
    in a distributed manner on
    `YARN <http://spark.apache.org/docs/latest/running-on-yarn.html>`_.
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
        self.use_spark = cfg.use_spark
        if self.use_spark:
            self.spark = self._create_spark_session()
        else:
            self.spark = None

    def _create_spark_session(self):
        '''Creates a Spark Session.'''
        from pyspark.sql import SparkSession
        return SparkSession.builder.\
            master(cfg.spark_master).\
            appName(self.__class__.__name__).\
            getOrCreate()

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
        pyspark.sql.DataFrame or pandas.DataFrame
            data frame with columns "mapobject_id" and "value" and
            a row for each mapobject
        '''
        if self.use_spark:
            return self._load_feature_values_spark(
                mapobject_type_name, feature_name
            )
        else:
            return self._load_feature_values_pandas(
                mapobject_type_name, feature_name
            )

    def _load_feature_values_spark(self, mapobject_type_name, feature_name):
        query = self._build_feature_values_query(
            mapobject_type_name, feature_name
        )
        lower, upper = self._determine_bounds(mapobject_type_name, feature_name)
        return self._read_table(
            table=query, n_partitions=100, lower_bound=lower, upper_bound=upper,
        )

    def _load_feature_values_pandas(self, mapobject_type_name, feature_name):
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
        data: pyspark.sql.DataFrame or pandas.DataFrame
            data frame with columns "label" and "mapobject_id"

        See also
        --------
        :class:`tmlib.models.feature.LabelValue`
        '''
        if self.use_spark:
            return self._save_label_values_spark(result_id, data)
        else:
            return self._save_label_values_pandas(result_id, data)

    def _save_label_values_spark(self, result_id, data):
        import pyspark.sql.functions as sp
        url = cfg.db_uri_spark.replace(
            'tissuemaps', 'tissuemaps_experiment_%s' % self.experiment_id
        )
        table = tm.LabelLayerValue.__table__.name
        formatted_data = data.select(data.label.alias('value'))
        formatted_data = data.withColumn('tool_result_id', sp.lit(result_id))
        formatted_data.write.jdbc(url=url, table=table, mode='append')

    def _save_label_values_pandas(self, result_id, data):
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

    @assert_type(mapobject_type_name='basestring', feature_names='list')
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
        pyspark.sql.DataFrame or pandas.DataFrame
            dataframe where columns are features and rows are mapobjects
            indexable by `mapobject_id` (*pandas* dataframes have a separate
            column for each feature, while *spark* dataframes have only one
            column named "feature" with
            :class:`pyspark.mllib.linalg.DenseVector` as required by classifiers
            of the :mod:`pyspark.ml` package)
        '''
        if self.use_spark:
            return self._load_feature_values_table_spark(
                mapobject_type_name, feature_names
            )
        else:
            return self._load_feature_values_table_pandas(
                mapobject_type_name, feature_names
            )

    def _load_feature_values_table_pandas(self, mapobject_type_name,
            feature_names):
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

    def _load_feature_values_table_spark(self, mapobject_type_name,
            feature_names):
        # feature_values = spark.read_table('feature_values')
        # features = spark.read_table('features')
        # mapobjects = spark.read_table('mapobjects')
        # mapobject_types = spark.read_table('mapobject_types')
        from pyspark.ml.feature import VectorAssembler
        for i, name in enumerate(feature_names):
            df = self._load_feature_values_spark(mapobject_type_name, name)
            # df = feature_values.\
            #     join(features, features.id==feature_values.feature_id).\
            #     join(mapobjects, mapobjects.id==feature_values.mapobject_id).\
            #     join(mapobject_types, mapobject_types.id==features.mapobject_type_id).\
            #     filter(features.name == name).\
            #     filter(mapobject_types.name == mapobject_type_name).\
            #     filter(mapobject_types.experiment_id == experiment_id)
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

    def calculate_unique_labels(self, predicted_labels):
        '''Calculates the set of unique label values.

        Parameters
        ----------
        predicted_labels: pyspark.sql.DataFrame or pandas.DataFrame
            data frame with column "label" and one row for each mapobject

        Returns
        -------
        List[float]
            unique label values accross all mapobjects
        '''
        if self.use_spark:
            import pyspark.sql.functions as sp
            stats = feature_values.\
                select(sp.collect_set('label')).\
                collect()
            return stats[0][0]
        else:
            return np.unique(predicted_labels.label).astype(float).tolist()
