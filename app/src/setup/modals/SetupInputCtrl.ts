class SetupInputCtrl {
    static $inject = ['task', 'description', 'widgetType', 'choices', '$uibModalInstance'];

    private input: any;

    constructor(private task: string,
                private description: string,
                private widgetType: string,
                private choices: any,
                private _$uibModalInstance: any) {
        this.task = task;
        this.description = description;
        this.widgetType = widgetType;
        this.choices = choices;
    }

    ok() {
        if (this.widgetType == null) {
            this.input = true;
        }
        // Resolves the result promise
        this._$uibModalInstance.close(this.input, 500);
    }

    cancel() {
        // Rejects the result promise
        this._$uibModalInstance.dismiss('cancel');
    }

}

angular.module('tmaps.ui').controller('SetupInputCtrl', SetupInputCtrl);
