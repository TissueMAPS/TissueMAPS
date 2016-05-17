import numpy as np
import pandas as pd
from abc import ABCMeta
from abc import abstractmethod
from pyspark.sql import DataFrameReader
from pyspark.ml.feature import VectorAssembler, VectorIndexer, StringIndexer
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator

from tmlib.models import FeatureValue, Feature, MapobjectType
from tmaps.extensions import db
from tmaps.extensions import spark
from tmaps.extensions.spark import db_url
from tmaps.tool import Result
from tmaps.tool import ScalarLabelLayer
from tmaps.tool import SupervisedClassifierLabelLayer

class ToolRequestHandler(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def process_request(self):
        pass


class Classifier(ToolRequestHandler):

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
            :py:class:`tmlib.models.MapobjectType`
        feature_names: List[str]
            names of selected features, see :py:class:`tmlib.models.Feature`

        Returns
        -------
        pandas.DataFrame
            data frame where columns are features named according
            to items of `feature_names` and rows are mapobjects indexable by
            `mapobject_ids`
        '''
        mapobject_type = db.session.query(MapobjectType).\
            filter_by(name=mapobject_type_name, experiment_id=experiment_id).\
            one()
        feature_values = db.session.query(
                Feature.name, FeatureValue.mapobject_id, FeatureValue.value
            ).\
            join(FeatureValue).\
            filter(
                (Feature.name.in_(feature_names)) &
                (Feature.mapobject_type_id == mapobject_type.id)).\
            all()
        feature_df_long = pd.DataFrame(feature_values)
        feature_df_long.columns = ['feature', 'mapobject', 'value']
        return pd.pivot_table(
            feature_df_long, values='value', index='mapobject',
            columns='feature'
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
            :py:class:`tmlib.models.MapobjectType`
        feature_names: List[str]
            names of selected features, see :py:class:`tmlib.models.Feature`

        Returns
        -------
        pyspark.sql.DataFrame
            data frame with "mapobject_id" and "features" columns, where
            "features" column has type
            :py:class:`pyspark.mllib.linalg.DenseVector`
        '''
        feature_values = spark.read_table('feature_values')
        features = spark.read_table('features')
        mapobjects = spark.read_table('mapobjects')
        mapobject_types = spark.read_table('mapobject_types')
        feature_names = feature_names

        for i, name in enumerate(feature_names):
            df = feature_values.\
                join(features, features.id==feature_values.feature_id).\
                join(mapobjects, mapobjects.id==feature_values.mapobject_id).\
                join(mapobject_types, mapobject_types.id==features.mapobject_type_id).\
                filter(features.name == name).\
                filter(mapobject_types.name == mapobject_type_name).\
                filter(mapobject_types.experiment_id == experiment_id)
            if i == 0:
                data = df.select(
                    feature_values.value.alias(name),
                    feature_values.mapobject_id
                )
            else:
                df = df.select(
                    feature_values.value.alias(name),
                    feature_values.mapobject_id.alias('%s_mapobject_id' % name)
                )
                ref_name = feature_names[0]
                on = data['mapobject_id'] == df['%s_mapobject_id' % name]
                data = data.join(df, on, 'inner').drop('%s_mapobject_id' % name)

        assembler = VectorAssembler(
            inputCols=feature_names, outputCol='features'
        )
        return assembler.transform(data).select('features', 'mapobject_id')


class SupervisedClassifier(Classifier):

    __metaclass__ = ABCMeta

    def label_feature_data_spark(self, feature_data, labeled_mapobjects):
        '''Add labels to `feature_data` for supervised classification.

        Parameters
        ----------
        feature_data: pyspark.sql.DataFrame
            data frame with "features" and "mapobject_id" columns as generated
            by :py:method:`tmserver.toolbox.classifier.Classfier.format_feature_data_spark`
        labeled_mapobjects: Tuple[int]
            ID and assigned label for each selected mapobject,
            see :py:class:`tmlib.models.Mapobject`

        Returns
        -------
        pyspark.sql.DataFrame
            subset of `feature_data` for selected mapobjects with additional
            column "label"
        '''
        labels = spark.sqlctx.createDataFrame(
            labeled_mapobjects, schema=['mapobject_id', 'label']
        )
        labeled_data = feature_data.join(
            labels, labels['mapobject_id'] == feature_data['mapobject_id']
        ).cache()
        return labeled_data

    def label_feature_data_sklearn(self, feature_data, labeled_mapobjects):
        '''Add labels to `feature_data` for supervised classification.

        Parameters
        ----------
        feature_data: pandas.DataFrame
            data frame where columns are features and rows are mapobjects
            as generated by
            :py:method:`tmserver.toolbox.classifier.Classfier.format_feature_data_sklearn`
        labeled_mapobjects: Tuple[int]
            ID and assigned label for each selected mapobject,
            see :py:class:`tmlib.models.Mapobject`

        Returns
        -------
        pandas.DataFrame
            subset of `feature_data` for selected mapobjects with additional
            column "label"
        '''
        labeled_mapobjects = np.array(labeled_mapobjects)
        ids = labeled_mapobjects[:, 0]
        labels = labeled_mapobjects[:, 1]
        labeled_feature_data = feature_data[~feature_data.index.isin(ids)]
        labeled_feature_data['label'] = labels
        return labeled_feature_data

    @abstractmethod
    def classify_spark(self, unlabeled_feature_data, labeled_feature_data):
        '''Trains a classifier for labeled mapobjects based on
        `labeled_feature_data` and predicts labels for all mapobjects based on
        `unlabeled_feature_data`.

        Parameters
        ----------
        unlabeled_feature_data: pyspark.sql.DataFrame
        labeled_feature_data: pyspark.sql.DataFrame

        Returns
        -------
        List[Tuple[int, str]]
            ID and predicted label for each mapobject
        '''
        pass

    @abstractmethod
    def classify_sklearn(self, unlabeled_feature_data, labeled_feature_data):
        '''Trains a classifier for labeled mapobjects based on
        `labeled_feature_data` and predicts labels for all mapobjects based on
        `unlabeled_feature_data`.

        Parameters
        ----------
        unlabeled_feature_data: pandas.DataFrame
        labeled_feature_data: pandas.DataFrame

        Returns
        -------
        List[Tuple[int, str]]
            ID and predicted label for each mapobject
        '''
        pass

    def process_request(self, payload, tool_session, experiment, use_spark=False):
        #m Get mapobject
        mapobject_type_name = payload['chosen_object_type']
        feature_names = payload['selected_features']
        labeled_mapobjects = list()
        color_map = dict()
        for cls in payload['training_classes']:
            labels = [(i, cls['name']) for i in cls['object_ids']]
            labeled_mapobjects.extend(labels)
            color_map[cls['name']] = cls['color']

        if use_spark:
            unlabeled_feature_data = self.format_feature_data_spark(
                experiment.id, mapobject_type_name, feature_names
            )
            labeled_feature_data = self.label_feature_data_spark(
                unlabeled_feature_data, labeled_mapobjects
            )
            predicted_labels = self.classify_spark(
                unlabeled_feature_data, labeled_feature_data
            )
        else:
            unlabeled_feature_data = self.format_feature_data_sklearn(
                experiment.id, mapobject_type_name, feature_names
            )
            labeled_feature_data = self.label_feature_data_sklearn(
                unlabeled_feature_data, labeled_mapobjects
            )
            predicted_labels = self.classify_sklearn(
                unlabeled_feature_data, labeled_feature_data
            )

        return Result(
            tool_session=tool_session,
            layer=SupervisedClassifierLabelLayer(
                labels=dict(predicted_labels), color_map=color_map
            )
        )


class UnsupervisedClassifier(Classifier):

    __metaclass__ = ABCMeta

    @abstractmethod
    def classify_spark(self, feature_data):
        '''Clusters mapobjects based on `feature_data`.

        Parameters
        ----------
        feature_data: pyspark.sql.DataFrame
            feature values
        k: int
            number of classes

        Returns
        -------
        List[Tuple[int, str]]
            ID and predicted label for each mapobject
        '''
        pass

    @abstractmethod
    def classify_sklearn(self, feature_data, k):
        '''Clusters mapobjects based on `feature_data`.

        Parameters
        ----------
        feature_data: pandas.DataFrame
            feature values
        k: int
            number of classes

        Returns
        -------
        List[Tuple[int, str]]
            ID and predicted label for each mapobject
        '''
        pass

    def process_request(self, payload, tool_session, experiment, use_spark=False):
        mapobject_type_name = payload['chosen_object_type']
        feature_names = payload['selected_features']
        k = payload['k']

        if use_spark:
            feature_data = self.format_feature_data_spark(
                experiment.id, mapobject_type_name, feature_names
            )
            predicted_labels = self.classify_spark(feature_data, k)
        else:
            feature_data = self.format_feature_data_sklearn(
                experiment.id, mapobject_type_name, feature_names
            )
            predicted_labels = self.classify_sklearn(feature_data, k)

        return Result(
            tool_session=tool_session,
            layer=ScalarLabelLayer(labels=dict(predicted_labels))
        )
