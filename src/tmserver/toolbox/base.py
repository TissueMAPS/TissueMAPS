'''Base classes for classification tools.'''
import numpy as np
import pandas as pd
from abc import ABCMeta
from abc import abstractmethod

import tmlib.models as tm

from tmserver.extensions import spark
from tmserver.tool import ToolResult
from tmserver.tool import ScalarLabelLayer
from tmserver.tool import SupervisedClassifierLabelLayer
from tmserver.tool import Tool


class Classifier(Tool):

    __metaclass__ = ABCMeta

    def format_feature_data_sklearn(self, experiment_id, mapobject_type_name,
            feature_names):
        '''Load feature values from database and bring the dataset into the
        format required by classifiers of the :py:package:`sklearn` package.

        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        mapobject_type_name: str
            name of the selected mapobject type, see
            :py:class:`tmlib.models.tm.MapobjectType`
        feature_names: List[str]
            names of selected features, see :py:class:`tmlib.models.tm.Feature`

        Returns
        -------
        pandas.DataFrame
            data frame where columns are features named according
            to items of `feature_names` and rows are mapobjects indexable by
            `mapobject_ids`
        '''
        with tm.utils.ExperimentSession(experiment_id) as session:
            mapobject_type_id = session.query(tm.MapobjectType.id).\
                filter_by(name=mapobject_type_name).\
                one()
            feature_values = session.query(
                    tm.Feature.name, tm.FeatureValue.mapobject_id, tm.FeatureValue.value
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

    def format_feature_data_spark(self, experiment_id, mapobject_type_name,
            feature_names):
        '''Load feature values from database and bring the dataset into the
        format required by classifiers of the :py:package:`pyspark.ml` package.

        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        mapobject_type_name: str
            name of the selected mapobject type, see
            :py:class:`tmlib.models.tm.MapobjectType`
        feature_names: List[str]
            names of selected features, see :py:class:`tmlib.models.tm.Feature`

        Returns
        -------
        pyspark.sql.DataFrame
            data frame with "mapobject_id" and "features" columns, where
            "features" column has type
            :py:class:`pyspark.mllib.linalg.DenseVector`
        '''
        # feature_values = spark.read_table('feature_values')
        # features = spark.read_table('features')
        # mapobjects = spark.read_table('mapobjects')
        # mapobject_types = spark.read_table('mapobject_types')
        for i, name in enumerate(feature_names):
            df = self.get_feature_values_spark(
                experiment_id, mapobject_type_name, name
            )
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

