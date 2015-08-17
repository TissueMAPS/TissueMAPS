angular.module('tmaps.main.auth')
// TODO: Add additional information such as first name, last name, etc.
.factory('User', [function() {
    function User(id, name) {
        this.id = id;
        this.name = name;
    }

    return User;
}]);
