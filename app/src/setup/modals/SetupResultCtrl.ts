class SetupResultCtrl {
    static $inject = ['response', 'task', '$uibModalInstance'];

    constructor(private response: boolean,
                private task: string,
                private _$uibModalInstance: any) {
        this.response = response;
        this.task = task;
    }

    cancel() {
        // Rejects the result promise
        this._$uibModalInstance.dismiss('cancel');
    }

}

angular.module('tmaps.ui').controller('SetupResultCtrl', SetupResultCtrl);
