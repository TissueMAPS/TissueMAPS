angular.module('tmaps.main')
.controller('DialogCtrl', ['title', 'message', function(title, message) {
    console.log(message);
    this.title = title;
    this.message = message;
}]);
