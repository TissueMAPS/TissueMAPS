class ResultCtrl {
    result: ToolResult;

    private _opacityInput: number;

    get opacityInput() {
        return this._opacityInput;
    }

    set opacityInput(v: number) {
        this._opacityInput = v;
        this.result.layer.opacity = v / 100;
    }

    static $inject = ['$scope'];

    constructor($scope: any) {
        this.result = $scope.result;
        this.opacityInput = this.result.layer.opacity * 100;
    }
}

angular.module('tmaps.ui').controller('ResultCtrl', ResultCtrl);
