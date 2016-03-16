interface ResultsSettingsScope extends ng.IScope {
    selectionBox: any;
    resultSettingsCtrl: ResultsSettingsCtrl;
}

class ResultsSettingsCtrl {

    viewport: Viewport;

    constructor() {}

    removeResult(result) {
        result.hide()
    }

}

angular.module('tmaps.ui').controller('ResultsSettingsCtrl', ResultsSettingsCtrl);
