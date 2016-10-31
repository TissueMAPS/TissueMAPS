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
angular.module('tmaps.ui')
.directive('tmSelectionSettings', function() {
    return {
        restrict: 'E',
        // Create a new scope for this directive but prototypically link
        // it with the parent viewport scope, s.t. the directive has access
        // to the viewer.
        scope: true,
        bindToController: true,
        controllerAs: 'selCtrl',
        controller: 'SelectionSettingsCtrl',
        templateUrl: '/templates/main/layerprops/selections/tm-selection-settings.html'
    };
});
