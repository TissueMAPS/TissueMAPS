angular.module('tmaps.ui').directive('tmAppbar', [function() {
    return {
        restrict: 'EA',
        controller: 'AppbarCtrl',
        controllerAs: 'appbarCtrl',
        templateUrl: '/src/tm-appbar.html',
        bindToController: true
    };
}]);

class AppbarCtrl {
}
angular.module('tmaps.ui').controller('AppbarCtrl', AppbarCtrl);
