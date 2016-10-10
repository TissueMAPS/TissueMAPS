angular.module('jtui.project')
.controller('ModuleSelectionCtrl', ['$scope', function($scope) {

    this.removeSelectedModules = function() {
        var selectedModules = $scope.selectionBox.getSelectedItems();
        console.log('selected modules: ', selectedModules)
        for (var i in selectedModules) {
                var mod = selectedModules[i].name;
                var ixHandles = $scope.project.handles.map(function(e) { 
                        return e.name;
                    }).indexOf(mod);
                var ixPipe = $scope.project.pipe.description.pipeline.map(function(e) { 
                        return e.name;
                    }).indexOf(mod);
                if (ixHandles > -1) {
                    var currentProject = $scope.project
                    console.log('remove module \"' + mod + '\"');
                    currentProject.handles.splice(ixHandles, 1);
                    currentProject.pipe.description.pipeline.splice(ixPipe, 1)
                    ixSelected = $scope.selectedModules.indexOf(mod.name);
                    $scope.selectedModules.splice(ixSelected, 1);
                    $scope.project = currentProject;
                    console.log('updated project:', currentProject)
                } else {
                    console.log('removal of modules \"' + mod + '\" failed');
                }
        }
    };

}]);
