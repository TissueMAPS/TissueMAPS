// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
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
class ResultsControlsCtrl {
    static $inject = ['$scope', '$stateParams'];

    constructor(private _$scope: ResultsSettingsScope, private _$stateParams) {
    }

    removeSelectedResults() {
        var $scope = this._$scope;
        var dao = new ToolResultDAO(this._$stateParams.experimentid);
        $scope.selectionBox.getSelectedItems().forEach((res) => {
            dao.delete(res.id).then(() => {
                $scope.resultsSettingsCtrl.viewer.deleteSavedResult(res);
            },
            (err) => {
                console.log(err);
            });
        });
    };

}

angular.module('tmaps.ui').controller('ResultsControlsCtrl', ResultsControlsCtrl);
