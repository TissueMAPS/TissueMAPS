class SetupInputCtrl {
    static $inject = ['title', 'message', 'widgetType', 'choices', '$uibModalInstance'];

    private value: any;

    constructor(private title: string,
                private message: string,
                private widgetType: string,
                private choices: any,
                private _$uibModalInstance: any) {
        this.title = title;
        this.message = message;
        this.widgetType = widgetType;
        this.choices = choices;
    }

    ok() {
        if (this.widgetType == null) {
            this.value = true;
        }
        // Resolves the result promise
        this._$uibModalInstance.close(this.value, 500);
    }

    cancel() {
        // Rejects the result promise
        this._$uibModalInstance.dismiss('cancel');
    }

}

angular.module('tmaps.ui').controller('SetupInputCtrl', SetupInputCtrl);
