class SetupInputCtrl {
    static $inject = ['task', 'description', 'choices', '$uibModalInstance'];

    private input: string;

    constructor(private task: string,
                private description: string,
                private choices: any,
                private _$uibModalInstance: any) {
        this.task = task;
        this.description = description;
        this.choices = choices;
    }

    ok() {
        // Resolves the result promise
        this._$uibModalInstance.close(this.input, 500);
    }

    cancel() {
        // Rejects the result promise
        this._$uibModalInstance.dismiss('cancel');
    }

}

angular.module('tmaps.ui').controller('SetupInputCtrl', SetupInputCtrl);
