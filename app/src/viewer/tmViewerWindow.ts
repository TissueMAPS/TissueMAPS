// the ViewCtrl on the tm-view div enables control over everything view related.
// For example, broadcasting messages to all UI elements in the view can be made using 
// $scope.viewCtrl.broadcast(msg, data);
angular.module('tmaps.ui').directive('tmViewerWindow', [function() {
    return {
        restrict: 'EA',
        controller: 'ViewerWindowCtrl',
        scope: true,
        controllerAs: 'viewerWindowCtrl',
        bindToController: true
    };
}]);

interface ViewerWindowScope extends ng.IScope {
    viewerWindowCtrl: ViewerWindowCtrl;
}

class ViewerWindowCtrl {
    static $inject = ['$scope', 'application', '$document'];

    private viewers: AppInstance[];

    constructor(public $scope: ViewerWindowScope,
                private application: Application,
                private $document: ng.IDocumentService) {
        this.viewers = application.appInstances;
    }

    selectViewer(viewer: AppInstance) {
        this.application.showViewer(viewer);
    }

    deleteViewer(viewer: AppInstance) {
        this.application.removeViewer(viewer);
    }

}
angular.module('tmaps.ui').controller('ViewerWindowCtrl', ViewerWindowCtrl);
