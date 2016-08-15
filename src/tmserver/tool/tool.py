import pandas as pd
from sqlalchemy import Column, String, Text
import importlib
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty

from tmlib.models import MainModel
from tmserver.serialize import json_encoder
from tmserver.extensions import spark


class Tool(object):

    '''Abstract base class for a tool.'''

    __metaclass__ = ABCMeta

    @staticmethod
    def _build_feature_values_query(mapobject_type_name, feature_name):
        # We run the actual query in SQL, since has way better performance
        # compared to loading the table and then filtering it via Spark
        # TODO: find a way around parsing raw SQL statements
        return '''
            (SELECT v.value, v.mapobject_id FROM feature_values AS v
            JOIN features AS f ON f.id=v.feature_id
            JOIN mapobject_types AS t ON t.id=f.mapobject_type_id
            WHERE f.name=\'{feature_name}\'
            AND t.name=\'{mapobject_type_name}\'
            ) as t
        '''.format(
            mapobject_type_name=secure_filename(mapobject_type_name),
            feature_name=secure_filename(feature_name)
        )

    def get_feature_values_spark(self, experiment_id, mapobject_type_name,
            feature_name):
        '''Selects all values from table "feature_values" for mapobjects of
        a given `mapboject_type` and for the feature with the given name.

        Parameters
        ----------
        experiment_id: int
            ID of the corresponding experiment
        mapobject_type_name: str
            name of the parent mapobject type
        feature_name: str
            name of the parent feature

        Returns
        -------
        pyspark.sql.DataFrame
            data frame with columns "mapobject_id" and "value"
        '''
        query = self._build_feature_values_query(
            mapobject_type_name, feature_name
        )
        return spark.read_table(query)

    def get_feature_values_sklearn(self, experiment_id, mapobject_type_name,
            feature_name):
        '''Selects all values from table "feature_values" for mapobjects of
        a given :py:class:`tmlib.models.MapbojectType` and
        :py:class:`tmlib.models.Feature`.

        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        mapobject_type_name: str
            name of the parent mapobject type
        feature_name: str
            name of the parent feature

        Returns
        -------
        pandas.DataFrame
            data frame with columns "mapobject_id" and "value" and a row for
            each mapobject
        '''
        with tm.utils.ExperimentSession(experiment_id) as session:
            feature_values = session.query(
                    tm.FeatureValue.mapobject_id, tm.FeatureValue.value
                ).\
                join(tm.Feature).\
                join(tm.MapobjectType).\
                filter(
                    tm.Feature.name == feature_name,
                    tm.MapobjectType.name == mapobject_type_name
                ).\
                all()
        return pd.DataFrame(feature_values, columns=['mapobject_id', 'value'])

    @abstractmethod
    def process_request(self, payload, session_id, experiment_id,
            use_spark=False):
        '''Processes a tool request sent by the client.

        Parameters
        ----------
        payload: dict
            an arbitrary mapping sent by the client tool
        session_id: int
            ID of the respective tool session, which enables persistence of
            information over multiple requests (e.g. for iterative classifier
            training)
        experiment_id: int
            ID of the processed experiment
        use_spark : boolean, optional
            whether processing should be performed via Apache Spark
            (default: ``False``)

        '''
        pass
