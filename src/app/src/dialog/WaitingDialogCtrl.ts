class WaitingDialogCtrl {
    static $inject = ['message', '$uibModalInstance'];

    constructor(public message: string,
                private _$uibModelInstance: any) {

    }

}

angular.module('tmaps.ui').controller('WaitingDialogCtrl', WaitingDialogCtrl);

