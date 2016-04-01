class DialogCtrl {
    static $inject = ['title', 'message', '$modalInstance'];

    constructor(public title: string,
                public message: string,
                private _$modalInstance: any) {
    }

    ok() {
        // Resolves the result promise
        this._$modalInstance.close(true);
    }

    cancel() {
        // Rejects the result promise
        this._$modalInstance.dismiss('cancel');
    }

}

angular.module('tmaps.ui').controller('DialogCtrl', DialogCtrl);
