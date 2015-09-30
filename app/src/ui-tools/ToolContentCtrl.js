angular.module('tmaps.tools')
.controller('ToolContentCtrl', ['$scope', 'toolConfig', '$rootScope', function($scope, toolConfig, $rootScope) {

    // The template of this URL will be included in this controller's template
    $scope.templateUrl = toolConfig.templateUrl;
    $scope.toolName = toolConfig.name || toolConfig.id;

    $rootScope.$on('toolRequestSent', function() {
        $scope.isRunning = true;
    });
    $rootScope.$on('toolRequestDone', function() {
        $scope.isRunning = false;
    });

}]);
