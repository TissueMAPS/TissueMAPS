interface ResultsSettingsScope extends ng.IScope {
    selectionBox: any;
    resultSettingsCtrl: ResultsSettingsCtrl;
    viewer: AppInstance;
}

class ResultsSettingsCtrl {

    results: ToolResult[];
    viewer: AppInstance;

    constructor() {}
}

angular.module('tmaps.ui').controller('ResultsSettingsCtrl', ResultsSettingsCtrl);
