(function() {

    angular.module('tmaps.shared.color', []);
    angular.module('tmaps.shared.auth', []);
    angular.module('tmaps.shared.services', []);
    angular.module('tmaps.shared.filters', []);
    angular.module('tmaps.shared.misc', []);

    angular.module('tmaps.shared', [
        // Dependencies
        'tmaps.shared.color',
        'tmaps.shared.auth',
        'tmaps.shared.services',
        'tmaps.shared.filters',
        'tmaps.thirdpartymodules',
        'tmaps.shared.misc'
        // Note that tmaps.shared must not depend on either tmaps.main or
        // tmaps.tools since this would lead to a ciruclar dependency.
    ]);

}());
