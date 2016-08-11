import pandas as pd
from sqlalchemy import Column, String, Text
import importlib
from abc import ABCMeta
from abc import abstractmethod

import tmlib.models as tm
from tmserver.serialize import json_encoder
from tmserver.model import Model
from tmserver.extensions import spark
from tmserver.extensions import db


class Tool(Model):
    __tablename__ = 'tools'

    name = Column(String(120), index=True)
    icon = Column(String(120))
    description = Column(Text)
    full_class_path = Column(String(120))

    def get_class(self):
        def import_from_str(name):
            components = name.split('.')
            mod_name = '.'.join(components[:2])
            mod = importlib.import_module(mod_name)
            return getattr(mod, components[2])
            # mod = __import__(components[0])
            # for comp in components[1:]:
            #     mod = getattr(mod, comp)
            # return mod
        cls = import_from_str(self.full_class_path)
        return cls

    def to_dict(self):
        return {
            'id': self.hash,
            'name': self.name,
            'description': self.description,
            'icon': self.icon
        }


@json_encoder(Tool)
def encode_tool(obj, encoder):
    return {
        'id': obj.hash,
        'name': obj.name,
        'description': obj.description,
        'icon': obj.icon
    }


class ToolRequestHandler(object):

    __metaclass__ = ABCMeta

    @staticmethod
    def _build_feature_values_query(experiment_id, mapobject_type_name, feature_name):
        # We run the actual query in SQL, since has way better performance
        # compared to loading the table and then filtering it via Spark
        # TODO: find a way around parsing raw SQL statements
        return '''
            (SELECT v.value, v.mapobject_id FROM feature_values AS v
            JOIN features AS f ON f.id=v.feature_id
            JOIN mapobject_types AS t ON t.id=f.mapobject_type_id
            WHERE f.name=\'{feature_name}\'
            AND t.name=\'{mapobject_type_name}\'
            AND t.experiment_id={experiment_id}
            ) as t
        '''.format(**locals())

    def get_feature_values_spark(self, experiment_id, mapobject_type_name, feature_name):
        """Selects all values from table "feature_values" for mapobjects of
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
        """
        query = self._build_feature_values_query(
            experiment_id, mapobject_type_name, feature_name
        )
        return spark.read_table(query)

    def get_feature_values_sklearn(self, experiment_id, mapobject_type_name, feature_name):
        """Selects all values from table "feature_values" for mapobjects of
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
        pandas.DataFrame
            data frame with columns "mapobject_id" and "value"
        """
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
    def process_request(self, payload, tool_session, experiment, use_spark=False):
        """
        Process a tool request sent by the client.

        Parameters
        ----------
        payload : dict
            An arbitrary dictionary sent by the client tool.
        tool_session : tmaps.tool.ToolSession
            A session of a specific tool. This object enables information
            to persists over multiple requests (e.g. for iterative classifier
            training).
        experiment : tmlib.models.Experiment
            The experiment from which the request was sent.
        use_spark : boolean
            If the tool should try to use Apache Spark for processing.

        """
        pass
