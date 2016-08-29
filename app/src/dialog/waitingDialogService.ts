class WaitingDialogService {
    static $inject = ['$uibModal', '$q'];

    constructor(private _$uibModal, private _$q) {

    }

    private showDialog(message: string) {
        var instance = this._$uibModal.open({
            templateUrl: '/src/dialog/waiting.html',
            controller: 'WaitingDialogCtrl',
            controllerAs: 'waiting',
            size: 'sm',
            resolve: {
                message: () => {
                    return message;
                }
            }
        });

        return instance;
    }

    show(message: string) {
        return this.showDialog(message);
    }

}

angular.module('tmaps.ui').service('waitingDialogService', WaitingDialogService);
