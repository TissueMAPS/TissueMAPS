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
angular.module('jtui.project')
.controller('ModuleSelectionCtrl', ['$scope', function($scope) {

    this.removeSelectedModules = function() {
        var selectedModules = $scope.selectionBox.getSelectedItems();
        // console.log('selected modules: ', selectedModules)
        for (var i in selectedModules) {
                var mod = selectedModules[i].name;
                var ixHandles = $scope.project.handles.map(function(e) { 
                        return e.name;
                    }).indexOf(mod);
                var ixPipe = $scope.project.pipe.description.pipeline.map(function(e) { 
                        return e.name;
                    }).indexOf(mod);
                if (ixHandles > -1) {
                    var currentProject = $scope.project
                    // console.log('remove module \"' + mod + '\"');
                    currentProject.handles.splice(ixHandles, 1);
                    currentProject.pipe.description.pipeline.splice(ixPipe, 1)
                    ixSelected = $scope.selectedModules.indexOf(mod.name);
                    $scope.selectedModules.splice(ixSelected, 1);
                    $scope.project = currentProject;
                    // console.log('updated project:', currentProject)
                } else {
                    // console.log('removal of modules \"' + mod + '\" failed');
                }
        }
    };

}]);
