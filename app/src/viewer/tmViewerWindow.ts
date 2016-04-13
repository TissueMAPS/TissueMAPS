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

    private viewers: Viewer[];

    constructor(public $scope: ViewerWindowScope,
                private application: Application,
                private $document: ng.IDocumentService) {
        this.viewers = application.viewers;
    }

    selectViewer(viewer: Viewer) {
        this.application.showViewer(viewer);
    }

    deleteViewer(viewer: Viewer) {
        this.application.removeViewer(viewer);
    }

}
angular.module('tmaps.ui').controller('ViewerWindowCtrl', ViewerWindowCtrl);
