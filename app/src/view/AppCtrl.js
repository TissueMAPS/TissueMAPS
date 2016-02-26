angular.module('tmaps.ui')
.controller('AppCtrl', ['application', 'uiState', 'authService', 'session', '$rootScope', 'loginDialogService',
            function(application, uiState, authService, session, $rootScope, loginDialogService) {
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

    this.getAppInstances = function() {
        return application.viewports;
    };

    this.isActiveInstanceByIndex = function(index) {
        return application.activeInstanceNumber == index;
    };

    this.isAppInstanceEmpty = function() {
        return self.getAppInstances().length === 0;
    };

}]);
