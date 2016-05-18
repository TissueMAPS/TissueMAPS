// angular.module('jtui.main')
// .controller('MainCtrl',
//     ['uiState', 'runnerService', 'authService', 'session', '$scope',
//         function(uiState, runnerService, authService, session, $scope) {
//     this.keyDown = function(keyEvent) {
//         switch (keyEvent.keyCode) {
//             case 17:
//                 uiState.pressedKeys.ctrl = true;
//                 break;
//             case 18:
//                 uiState.pressedKeys.alt = true;
//                 break;
//             case 16:
//                 uiState.pressedKeys.shift = true;
//                 break;
//         }
//     };

//     this.keyUp = function(keyEvent) {
//         switch (keyEvent.keyCode) {
//             case 17:
//                 uiState.pressedKeys.ctrl = false;
//                 break;
//             case 18:
//                 uiState.pressedKeys.alt = false;
//                 break;
//             case 16:
//                 uiState.pressedKeys.shift = false;
//                 break;
//         }
//     };

//     this.isUserAuthenticated = function() {
//         return authService.isAuthenticated();
//     };

//     this.logout = function() {
//         return authService.logout();
//     };

//     this.getUser = function() {
//         return session.getUser();
//     };
// }]);
