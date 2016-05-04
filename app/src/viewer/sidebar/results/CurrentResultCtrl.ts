class CurrentResultCtrl {
    results: ToolResult[] = [];

    static $inject = ['$scope'];

    constructor($scope: any) {
        $scope.$watch('viewer.currentResult', (newVal) => {
            if (newVal) {
                this.results = [newVal];
            } else {
                this.results = [];
            }
        })
    }
}

angular.module('tmaps.ui').controller('CurrentResultCtrl', CurrentResultCtrl);
