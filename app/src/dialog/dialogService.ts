class DialogService {
    static $inject = ['$uibModal', '$q'];

    constructor(private _$uibModal, private _$q) {

    }

    private showDialog(title, message) {
        var instance = this._$uibModal.open({
            templateUrl: '/src/dialog/dialog.html',
            controller: 'DialogCtrl',
            controllerAs: 'dialog',
            resolve: {
                title: () => {
                    return title;
                },
                message: () => {
                    return message;
                }
            }
        });

        return instance.result;
    }

    error(message: string) {
        return this.showDialog('Error', message);
    }

    warning(message: string) {
        return this.showDialog('Warning', message);
    }

}

angular.module('tmaps.ui').service('dialogService', DialogService);
