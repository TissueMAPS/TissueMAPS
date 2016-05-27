angular.module('jtui.module')
.controller('ModuleCtrl', ['$scope', 'moduleService',
            function ($scope, moduleService) {

	moduleService.modules.then(function (modules) {
		$scope.modules = modules;
        for (i in $scope.modules) {
            var filename = $scope.modules[i].pipeline.source;
            $scope.modules[i].language = filename.split('.').pop();
        }
	});

	$scope.onDragComplete = function (data, evt) {
       console.log("drag success, data:", data);
    };

}]);
