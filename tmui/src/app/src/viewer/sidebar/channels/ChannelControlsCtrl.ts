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
angular.module('tmaps.ui')
/**
 * A controller to manage the control bar in the channel settings
 * section of the sidebar.
 * This controller has access to the selected items (= channel layers in
 * this case) since it is part of the selection box.
 */
.controller('ChannelControlsCtrl',
            ['$scope', 'removeLayerService',
            function($scope, removeLayerService) {

    this.removeSelectedChannels = function() {
        var sel = $scope.selectionBox.getSelectedItems();
        removeLayerService.removeChannelsAfterPrompt(sel);
    };

}]);

