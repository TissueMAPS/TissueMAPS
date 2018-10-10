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
interface ClusterScope extends ToolWindowContentScope {
    featureWidget: FeatureSelectionWidgetCtrl;
    mapobjectTypeWidget: MapobjectTypeWidgetCtrl;
}

class ClusteringCtrl extends ToolCtrl {
    static $inject = ['$scope', 'viewer'];

    nClusters: number = 2;
    algorithm: string = 'kmeans';

    constructor(public $scope: ClusterScope,
                public viewer: Viewer) {
        super();
    }

    doCluster() {
        var selectedFeatures = this.$scope.featureWidget.selectedFeatures;
        this.sendRequest({
            chosen_object_type: this.$scope.mapobjectTypeWidget.selectedType,
            selected_features: selectedFeatures,
            options: {
                k: this.nClusters,
                method: this.algorithm
            }
        });
    }
}
