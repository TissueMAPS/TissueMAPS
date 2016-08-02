interface ResultsSettingsScope extends ng.IScope {
    selectionBox: any;
    resultsSettingsCtrl: ResultsSettingsCtrl;
    viewer: Viewer;
}

class ResultsSettingsCtrl {

    results: ToolResult[];
    viewer: Viewer;

    constructor() {}
}

angular.module('tmaps.ui').controller('ResultsSettingsCtrl', ResultsSettingsCtrl);
