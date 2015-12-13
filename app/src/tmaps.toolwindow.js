(function() {
    var module = angular.module('tmaps.toolwindow', [
        'tmaps.core',
        'tmaps.ui',
        'highcharts-ng'
    ]);

    module.config(['$httpProvider', function($httpProvider) {
        $httpProvider.interceptors.push('authInterceptor');
    }]);

    module.config(['$stateProvider', '$urlRouterProvider',
                   function($stateProvider, $urlRouterProvider) {
        $urlRouterProvider.otherwise('/');

        $stateProvider
        .state('tool', {
            url: '/',
            templateUrl: '/src/toolwindow/tool-content.html',
            controller:  'ToolContentCtrl',
        });
    }]);

    module.run(['$window', function($window) {
        if (!angular.isDefined($window.init)) {
            console.log(
                'There is no global TissueMAPS helper object for this tool window! ' +
                'The tool won\'t function properly!'
            );
        }
    }]);

}());

