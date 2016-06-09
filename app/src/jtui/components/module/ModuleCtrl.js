angular.module('jtui.module')
.controller('ModuleCtrl', ['$scope', '$uibModal', 'moduleService',
            function ($scope, $uibModal, moduleService) {

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

    var codeIsOpen = false;
    $scope.showSourceCode = function (module) {
        console.log(module)

        if (codeIsOpen) return;
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/module/modals/code.html',
            size: 'lg',
            resolve: {
                code: ['moduleService', function(moduleService){
                    return moduleService.getModuleSourceCode(
                        module.pipeline.source
                    );
                }],
                language: function () {
                    return module.language;
                },
                name: function () {
                    return  module.name;
                }
            },
            controller: 'CodeCtrl'
        });

        codeIsOpen = true;

        modalInst.result.then(function () {
            codeIsOpen = false;
        }, function () {
            codeIsOpen = false;
        });
    };

}]);
