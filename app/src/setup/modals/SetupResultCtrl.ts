class SetupResultCtrl {
    static $inject = ['title', 'response', '$uibModalInstance'];

    constructor(private title: string,
                private response: boolean,
                private _$uibModalInstance: any) {
        this.response = response;
        this.title = title;
    }

    cancel() {
        // Rejects the result promise
        this._$uibModalInstance.dismiss('cancel');
    }

}

angular.module('tmaps.ui').controller('SetupResultCtrl', SetupResultCtrl);
