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
angular.module('jtui.module')
.controller('ModuleCtrl', ['$scope', '$uibModal', 'moduleService',
            function ($scope, $uibModal, moduleService) {

	moduleService.modules.then(function (modules) {
		$scope.modules = modules;
        for (i in $scope.modules) {
            var filename = $scope.modules[i].pipeline.source;
            $scope.modules[i].language = filename.split('.').pop();
        }
	});

	$scope.onDragComplete = function (data, evt) {
       // console.log("drag success, data:", data);
    };

    var codeIsOpen = false;
    $scope.showSourceCode = function (module) {

        if (codeIsOpen) return;
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/module/modals/code.html',
            size: 'lg',
            resolve: {
                code: ['moduleService', function(moduleService){
                    return moduleService.getModuleSourceCode(
                        module.pipeline.source
                    );
                }],
                language: function () {
                    return module.language;
                },
                name: function () {
                    return  module.name;
                }
            },
            controller: 'CodeCtrl'
        });

        codeIsOpen = true;

        modalInst.result.then(function () {
            codeIsOpen = false;
        }, function () {
            codeIsOpen = false;
        });
    };

}]);
