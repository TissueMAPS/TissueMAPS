import numpy as np
from sklearn.grid_search import GridSearchCV
from sklearn import svm, cross_validation

from tools.classifier.classifier import SupervisedClassifier


class SVM(SupervisedClassifier):

    def classify_sklearn(self, unlabeled_feature_data, labeled_feature_data):
        n_samples = labeled_feature_data.shape[0]
        n_folds = min(n_samples / 2, 10)

        X = labeled_feature_data.drop('label')
        y = labeled_feature_data.label
        folds = cross_validation.StratifiedKFold(y, n_folds=n_folds)
        searchspace = [
            {'kernel': ['rbf'], 'C': np.linspace(0.1, 1, 10), 'gamma': [0.001, 0, 1]},
            {'kernel': ['linear'], 'C': np.linspace(0.1, 1, 10)}
        ]
        clf = svm.SVC()
        gs = GridSearchCV(clf, searchspace, cv=folds)
        gs.fit(X, y)

        predictions = gs.predict(unlabeled_feature_data)
        return zip(labeled_feature_data.index.tolist(), predictions.tolist())

    def classify_spark(self, unlabeled_feature_data, labeled_feature_data):
        raise AttributeError(
            'Tool "%s" didn\'t implement "classify_spark" method.'
            % self.__class__.__name__
        )
