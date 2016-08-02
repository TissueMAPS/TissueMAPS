class DialogCtrl {
    static $inject = ['title', 'message', '$uibModalInstance'];

    constructor(public title: string,
                public message: string,
                private _$uibModelInstance: any) {
    }

    ok() {
        // Resolves the result promise
        this._$uibModelInstance.close(true);
    }

    cancel() {
        // Rejects the result promise
        this._$uibModelInstance.dismiss('cancel');
    }

}

angular.module('tmaps.ui').controller('DialogCtrl', DialogCtrl);
