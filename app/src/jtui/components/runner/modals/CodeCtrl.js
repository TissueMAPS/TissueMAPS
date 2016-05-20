angular.module('jtui.runner')
.controller('CodeCtrl', ['$scope', 'code', 'language', 'name', 'marked', '$modalInstance',
    function($scope, code, language, name, marked, $modalInstance) {

    $scope.code = marked('```' + language + '\n' + code + '\n' + '```');
    // console.log('code: ', code)
    $scope.name = name;
    $scope.language = language;

    $scope.close = function (result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
