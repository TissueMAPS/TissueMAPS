interface ToolOptions {
    chosenMapObjectType: MapObjectType;
}

interface ToolWindowScope extends ng.IScope {
    tool: Tool;
    isRunning: boolean;
}

class ToolWindowCtrl {

    static $inject = ['$scope', '$rootScope'];

    constructor(private _$scope: ToolWindowScope,
                private _$rootScope: ng.IRootScopeService) {

        // this._$scope.toolOptions = {
        //     // chosenMapObjectType: undefined
        // };

        this._$rootScope.$on('toolRequestSent', () => {
            this._$scope.isRunning = true;
        });

        this._$rootScope.$on('toolRequestDone', () => {
            this._$scope.isRunning = false;
        });
    }
}

angular.module('tmaps.toolwindow').controller('ToolWindowCtrl', ToolWindowCtrl);
