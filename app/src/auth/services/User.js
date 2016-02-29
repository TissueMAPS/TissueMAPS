angular.module('tmaps.auth')
// TODO: Add additional information such as first name, last name, etc.
.factory('User', ['USER_ROLES', function(USER_ROLES) {
    function User(id, name, roles) {
        this.id = id;
        this.name = name;
        this.roles = roles;
    }

    User.prototype.isAdmin = function() {
        return _(this.roles).contains(USER_ROLES.admin);
    };

    return User;
}]);
