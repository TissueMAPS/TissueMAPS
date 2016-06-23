import numpy as np
import time
from sklearn.grid_search import GridSearchCV
from sklearn import svm, cross_validation

from tmserver.extensions import spark
from toolbox.classifier import SupervisedClassifier


class SVM(SupervisedClassifier):

    def classify_sklearn(self, unlabeled_feature_data, labeled_feature_data):
        n_samples = labeled_feature_data.shape[0]
        n_folds = min(n_samples / 2, 3)

        X = labeled_feature_data.drop('label', axis=1)
        y = labeled_feature_data.label
        folds = cross_validation.StratifiedKFold(y, n_folds=n_folds)
        # TODO: kernel, consider using LinearSVC
        searchspace = [
            {'kernel': ['linear', 'rbf'], 'C': np.linspace(0.1, 1, 5)}
        ]
        clf = svm.SVC()
        gs = GridSearchCV(clf, searchspace, cv=folds)
        print 'train SVM model'
        t = time.time()
        gs.fit(X, y)
        print 'fitting model took %f seconds' % (time.time() - t)

        print 'apply trained model'
        t = time.time()
        predictions = gs.predict(unlabeled_feature_data)
        print 'predicting labels took %f seconds' % (time.time() - t)
        return zip(unlabeled_feature_data.index.tolist(), predictions.tolist())

    def classify_spark(self, unlabeled_feature_data, labeled_feature_data):
        from pyspark.ml.feature import StringIndexer
        from pyspark.mllib.regression import LabeledPoint
        from pyspark.mllib.classification import SVMWithSGD
        # NOTE: SVM is only available in MLLIB package, which works with RDDs
        # rather than DataFrames
        label_indexer = StringIndexer(
                inputCol='label', outputCol='indexedLabel'
            ).\
            fit(labeled_feature_data)

        label_df = label_indexer.transform(labeled_feature_data)
        label_mapping = {
            row.indexedLabel: row.label
            for row in label_df.\
                select('label', 'indexedLabel').\
                distinct().\
                collect()
        }
        labeled_feature_data = label_df.\
            select('indexedLabel', 'features').\
            map(lambda row: LabeledPoint(row.indexedLabel, row.features))
        svm = SVMWithSGD.train(labeled_feature_data, intercept=True)
        predictions = unlabeled_feature_data.\
            select('mapobject_id', 'features').\
            map(lambda row: (row.mapobject_id, label_mapping[svm.predict(row.features)]))
        return predictions.collect()

