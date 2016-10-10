class SetupOutputCtrl {
    static $inject = ['stdout', 'stderr', '$uibModalInstance'];

    constructor(private stdout: string,
                private stderr: boolean,
                private _$uibModalInstance: any) {
    }

    cancel() {
        // Rejects the result promise
        this._$uibModalInstance.dismiss('cancel');
    }

}

angular.module('tmaps.ui').controller('SetupOutputCtrl', SetupOutputCtrl);

