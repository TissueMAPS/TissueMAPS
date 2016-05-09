from sklearn.ensemble import RandomForestClassifier
from sklearn.grid_search import GridSearchCV
from sklearn import cross_validation
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, VectorIndexer, StringIndexer
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator

from tools.classifier.classifier import SupervisedClassifier


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
        )
        fi_model = feature_indexer.fit(training_set)
        label_indexer = StringIndexer(
            inputCol='label', outputCol='indexedLabel'
        )
        li_model = label_indexer.fit(training_set)

        rf = RandomForestClassifier(
            labelCol='indexedLabel', featuresCol='indexedFeatures'
        )
        grid = ParamGridBuilder().\
            addGrid(rf.maxDepth, [3, 5, 7]).\
            addGrid(rf.numTrees, [10, 20, 30]).\
            build()

        pipeline = Pipeline(stages=[fi_model, li_model, rf])
        evaluator = MulticlassClassificationEvaluator(
            labelCol='indexedLabel', predictionCol='prediction', metricName='f1'
        )
        crossval = CrossValidator(
            estimator=pipeline, estimatorParamMaps=grid,
            evaluator=evaluator, numFolds=3
        )
        model = crossval.fit(training_set)
        test_set = assembler.transform(data)
        predictions = model.transform(test_set).\
            select('prediction', 'mapobject_id')
        result = predictions.collect()
        return [(r.mapobject_id, r.prediction) for r in result]

