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
.controller('CodeCtrl', ['$scope', 'code', 'language', 'name', 'marked', '$uibModalInstance',
    function($scope, code, language, name, marked, $uibModalInstance) {

    $scope.code = '```' + language + '\n' + code + '\n' + '```';
    // $scope.code = marked('```' + language + '\n' + code + '\n' + '```');
    $scope.name = name;
    $scope.language = language;

    $scope.close = function (result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
