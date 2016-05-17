from sklearn.ensemble import RandomForestClassifier
from sklearn.grid_search import GridSearchCV
from sklearn import cross_validation
from pyspark.ml import Pipeline
<<<<<<< HEAD
from pyspark.ml.feature import StringIndexer
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.feature import VectorIndexer
from pyspark.ml.feature import IndexToString
=======
from pyspark.ml.feature import VectorAssembler, VectorIndexer, StringIndexer
>>>>>>> 72a63698b7ddb98cdc3310f889de32d0518c9eef
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator

from tools.classifier import SupervisedClassifier


class RandomForest(SupervisedClassifier):

    def classify_sklearn(self, unlabeled_feature_data, labeled_feature_data):
        n_samples = labeled_feature_data.shape[0]
        n_folds = min(n_samples / 2, 10)

        X = labeled_feature_data.drop('label')
        y = labeled_feature_data.label
        folds = cross_validation.StratifiedKFold(y, n_folds=n_folds)
        grid = {
            'max_depth': [3, 5, 7],
            'max_features': [1, 3, 10],
            'min_samples_split': [1, 3, 10],
            'min_samples_leaf': [1, 3, 10]
        }
        clf = RandomForestClassifier()
        gs = GridSearchCV(clf, grid, cv=folds)
        gs.fit(X, y)

        predictions = gs.predict(unlabeled_feature_data)
        return zip(labeled_feature_data.index.tolist(), predictions.tolist())

    def classify_spark(self, unlabeled_feature_data, labeled_feature_data):
        feature_indexer = VectorIndexer(
                inputCol='features', outputCol='indexedFeatures', maxCategories=2
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

        rf = RandomForestClassifier(
            labelCol='indexedLabel', featuresCol='indexedFeatures'
        )
        grid = ParamGridBuilder().\
            addGrid(rf.maxDepth, [3, 5, 7]).\
            addGrid(rf.numTrees, [10, 20, 30]).\
            build()

        pipeline = Pipeline(
            stages=[feature_indexer, label_indexer, rf]
        )
        evaluator = MulticlassClassificationEvaluator(
            labelCol='indexedLabel', predictionCol='prediction',
            metricName='f1'
        )
        crossval = CrossValidator(
            estimator=pipeline, estimatorParamMaps=grid,
            evaluator=evaluator, numFolds=3
        )
        model = crossval.fit(labeled_feature_data)
        predictions = model.transform(unlabeled_feature_data)
        result = predictions.select('mapobject_id', 'prediction').collect()
        return [(r.mapobject_id, label_mapping[r.prediction]) for r in result]
