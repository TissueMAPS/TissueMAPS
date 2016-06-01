angular.module('jtui.runner')
.controller('CodeCtrl', ['$scope', 'code', 'language', 'name', 'marked', '$uibModalInstance',
    function($scope, code, language, name, marked, $uibModalInstance) {

    $scope.code = '```' + language + '\n' + code + '\n' + '```';
    // $scope.code = marked('```' + language + '\n' + code + '\n' + '```');
    $scope.name = name;
    $scope.language = language;

    $scope.close = function (result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
