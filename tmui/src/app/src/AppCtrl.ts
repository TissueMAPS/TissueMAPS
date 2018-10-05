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
.controller('AppCtrl', ['application', 'uiState', 'authService', 'session', '$rootScope', 'loginDialogService', '$state',
            function(application, uiState, authService, session, $rootScope, loginDialogService, $state) {
    var self = this;

    /**
     * User management
     */
    this.isUserAuthenticated = function() {
        return authService.isAuthenticated();
    };
    this.getUser = session.getUser;
    this.logout = function() {
        authService.logout();
    };
    this.login = function() {
        loginDialogService.showDialog();
    };

    this.keyDown = function(keyEvent) {
        switch (keyEvent.keyCode) {
            case 17:
                uiState.pressedKeys.ctrl = true;
                break;
            case 18:
                uiState.pressedKeys.alt = true;
                break;
            case 16:
                uiState.pressedKeys.shift = true;
                break;
        }
    };

    this.keyUp = function(keyEvent) {
        switch (keyEvent.keyCode) {
            case 17:
                uiState.pressedKeys.ctrl = false;
                break;
            case 18:
                uiState.pressedKeys.alt = false;
                break;
            case 16:
                uiState.pressedKeys.shift = false;
                break;
        }
    };

    this.getViewers = function() {
        return application.viewports;
    };

    this.isActiveInstanceByIndex = function(index) {
        return application.activeInstanceNumber == index;
    };

    this.isViewerEmpty = function() {
        return self.getViewers().length === 0;
    };

}]);
