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
