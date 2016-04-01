class DialogService {
    static $inject = ['$modal', '$q'];

    constructor(private _$modal, private _$q) {

    }

    private showDialog(title, message) {
        var instance = this._$modal.open({
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
