class DialogService {
    static $inject = ['$uibModal', '$q'];

    constructor(private _$uibModal, private _$q) {

    }

    private showDialog(title, message, size) {
        var instance = this._$uibModal.open({
            templateUrl: '/src/dialog/dialog.html',
            controller: 'DialogCtrl',
            controllerAs: 'dialog',
            size: size,
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
        return this.showDialog('Error', message, 'sm');
    }

    warning(message: string) {
        return this.showDialog('Warning', message, 'sm');
    }

    info(message: string) {
        return this.showDialog('Info', message, 'sm');
    }

}

angular.module('tmaps.ui').service('dialogService', DialogService);
