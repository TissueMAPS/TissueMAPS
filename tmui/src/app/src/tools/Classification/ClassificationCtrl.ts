// Copyright (C) 2016-2018 University of Zurich.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
interface ClassificationScope extends ToolWindowContentScope {
    randomForest: ClassificationCtrl;
    featureWidget: FeatureSelectionWidgetCtrl;
    mapobjectTypeWidget: MapobjectTypeWidgetCtrl;
    classSelectionWidget: ClassSelectionWidgetCtrl;
}

class ClassificationCtrl extends ToolCtrl {
    static $inject = ['$scope', 'viewer'];

    method: string = 'randomforest';
    nCrossvalidations: number = 5;
    name: string = 'Classification';
    runClassifier: boolean = true;
    saveLabels: boolean = true;

    constructor(public $scope: ClassificationScope,
                public viewer: Viewer) {
        super();
    }

    doClassify() {
        // Build the request object
        var selectedFeatures = this.$scope.featureWidget.selectedFeatures;

        var trainingClasses = [];
        this.$scope.classSelectionWidget.classes.forEach((cls) => {
            trainingClasses.push({
                name: cls.name,
                object_ids: cls.mapobjectIds,
                color: cls.color.toHex()
            });
        });

        console.log(this.runClassifier);
        console.log(this.saveLabels);

        if(this.saveLabels){
          this.sendRequest({
              chosen_object_type: this.$scope.mapobjectTypeWidget.selectedType,
              selected_features: selectedFeatures,
              training_classes: trainingClasses,
              options: {
                  method: this.method,
                  n_fold_cv: this.nCrossvalidations
              },
              task: 'saveLabels',
              name: this.name
          });
        }

        if(this.runClassifier){
          this.sendRequest({
              chosen_object_type: this.$scope.mapobjectTypeWidget.selectedType,
              selected_features: selectedFeatures,
              training_classes: trainingClasses,
              options: {
                  method: this.method,
                  n_fold_cv: this.nCrossvalidations
              },
              task: 'classification',
              name: this.name
          });
        }
    }
}
