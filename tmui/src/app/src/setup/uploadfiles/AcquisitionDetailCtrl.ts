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
class AcquisitionDetailCtrl {

    newFiles: MicroscopeFile[] = [];
    filesDropped: boolean;

    static $inject = ['acquisition', '$state', '$http', '$q', '$stateParams'];

    constructor(public acquisition: Acquisition, private _$state,
                private _$http, private _$q, private _$stateParams) {
        this.filesDropped = false;
        acquisition.getUploadedFileCount()
        .then((count) => {
            acquisition.nFiles = count;
        })
    }

    filterValidFiles(files: {name: string;}[]) {
        console.log('validate files')
        var url = '/api/experiments/' + this._$stateParams.experimentid +
            '/acquisitions/' + this.acquisition.id + '/upload/validity-check';
        return this._$http.post(url, {
            files: files.map((f) => {
                return {name: f.name};
            })
        })
        .then((resp) => {
            var isValid = resp.data.is_valid;
            var validFiles = [];
            for (var i = 0; i < files.length; i++) {
                if (isValid[i]) {
                    validFiles.push(files[i]);
                }
            }
            return validFiles;
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    dropFiles(files) {
        console.log(files.length + ' files dropped')
        this.filesDropped = true;
        var newFileNames = this.newFiles.map((f) => {
            return f.name;
        });
        var filteredFiles = files.filter((f) => {
            return newFileNames.indexOf(f.name) == -1;
        });
        this.filterValidFiles(filteredFiles)
        .then((validFiles) => {
            validFiles.forEach((f) => {
                f.status = 'WAITING';
                this.newFiles.push(f);
            });
        });
    }

    uploadFiles() {
        if (this.newFiles.length !== 0) {
            this.acquisition.uploadFiles(this.newFiles)
            .then((ok) => {
                if (ok) {
                    console.log('All files uploaded');
                }
            })
            .catch((err) => {
                console.log(err);
            });
        }
    }

    clearFiles() {
        this.newFiles.splice(0, this.newFiles.length);
        this.filesDropped = false;
    }

}


angular.module('tmaps.ui')
.controller('AcquisitionDetailCtrl', AcquisitionDetailCtrl);
