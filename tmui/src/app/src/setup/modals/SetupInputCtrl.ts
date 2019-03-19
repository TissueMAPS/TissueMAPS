// Copyright (C) 2016-2018 University of Zurich.
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
