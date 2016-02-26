angular.module('tmaps.ui')
.controller('DialogCtrl', ['title', 'message', function(title, message) {
    console.log(message);
    this.title = title;
    this.message = message;
}]);
