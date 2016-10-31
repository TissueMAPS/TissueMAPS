// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
