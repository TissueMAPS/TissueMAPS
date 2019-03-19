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
/**
 * A file that was produced by a microscope. This can be a metadata file or
 * an image file.
 */
interface MicroscopeFile {
    name: string;
    status: string;
}

/**
 * Constructor arguments for an acquisition.
 */
interface AcquisitionArgs {
    id: string;
    name: string;
    status: string;
    description: string;
}

class Acquisition {
    id: string;
    name: string;
    description: string;
    status: string;
    files: MicroscopeFile[] = [];
    nFiles: number;
    experimentId: string;

    private _uploader: any;
    private _$stateParams: any;
    private _$http: ng.IHttpService;
    private _$q: ng.IQService;

    /**
     * Construct a new acquisition.
     *
     * @class Acquisition
     * @classdesc An acquisition represents a collection of imagefiles and
     * metadata files produced by a single microscope acquisition run.
     * @param {AcquisitionArgs} args - Constructor arguments.
     */
    constructor(args: AcquisitionArgs) {

        _.extend(this, args);

        this._$stateParams = $injector.get<any>('$stateParams');
        this._$http = $injector.get<ng.IHttpService>('$http');
        this._$q = $injector.get<ng.IQService>('$q');
        this._uploader = $injector.get<any>('Upload');
        this._uploader.setDefaults({ngfMinSize: 0, ngfMaxSize: 5000000000});
        this._uploader.defaults.blobUrlsMaxQueueSize = 10;  // default: 200
        this._uploader.defaults.blobUrlsMaxMemory = 5000000000;
    }

    fetchExistingFiles(): ng.IPromise<MicroscopeFile[]> {
        this.clearFiles();
        var imageUrl = '/api/experiments/' + this._$stateParams.experimentid +
            '/acquisitions/' + this.id + '/images';
        var metaDataUrl = '/api/experiments/' + this._$stateParams.experimentid +
            '/acquisitions/' + this.id + '/metadata';
        return this._$q.all({
            imageFiles: this._$http.get(imageUrl),
            metaDataFiles: this._$http.get(metaDataUrl)
        }).then((responses: any) => {
            var imageFiles = responses.imageFiles.data.data.filter((f) => {
                return f.status == 'COMPLETE';
            });
            var metaDataFiles = responses.metaDataFiles.data.data.filter((f) => {
                return f.status == 'COMPLETE';
            });
            var files = Array.prototype.concat(imageFiles, metaDataFiles)
            this.files = files;
            this.nFiles = this.files.length;
            return files;
        });
    }

    getUploadedFileCount(): ng.IPromise<number> {
        var url = '/api/experiments/' + this._$stateParams.experimentid +
            '/acquisitions/' + this.id + '/upload/count';
        return this._$http.get(url)
        .then((resp: any) => {
            // console.log('number of uploaded files: ', resp.data.data)
            return resp.data.data;
        });
    }

    /**
     * Upload a mutiple files. This method has to be called after the files
     * have been registered, i.e. created server-side.
     */
    private _uploadRegisteredFiles(newFiles): any {
        var url = '/api/experiments/' + this._$stateParams.experimentid +
            '/acquisitions/' + this.id + '/microscope-file';
        var $window = $injector.get<ng.IWindowService>('$window');
        var $timeout = $injector.get<any>('$timeout');
        this.status = 'UPLOADING';
        var namesUploadedFiles = this.files.map(function(f) {
            return f.name;
        });
        angular.forEach(newFiles, (file) => {
            if (namesUploadedFiles.indexOf(file.name) != -1) {
                // Skip files that were already uploaded.
                file.progress = 100;
                file.status = 'COMPLETE';
            } else {
                this._uploader.upload({
                    url: url,
                    // resumeSizeUrl: url + '/status'
                    header: {
                        'Authorization':
                            'JWT ' + $window.sessionStorage['token']
                    },
                    file: file
                })
                .then((response) => {
                    $timeout(function () {
                        file.result = response.data;
                    });
                }, (response) => {
                    if (response.status > 0)
                        file.status = 'FAILED';
                        console.log(response.status + ': ' + response.data)
                }, (evt) => {
                    file.progress = Math.round(100.0 * evt.loaded / evt.total);
                    file.status = 'UPLOADING';
                    if (file.progress == 100) {
                        file.status = 'COMPLETE';
                        if (namesUploadedFiles.indexOf(file.name) == -1) {
                            this.files.push(<MicroscopeFile>{
                                name: file.name, status: 'COMPLETE'
                            });
                            namesUploadedFiles.push(file.name)
                            this.nFiles = this.nFiles + 1;
                        }
                    }
                });
            }
        });
    }

    /**
     * Clear all files on this object (only client-side).
     */
    clearFiles() {
        this.files.splice(0, this.files.length);
    }

    countCompleted() {
        return this.files.filter((f) => {
            return f.status == 'COMPLETE';
        }).length
    }
    /**
     * Register files to be uploaded. This will create server-side
     * objects for all the files. Only files that were registered can be 
     * uploaded.
     */
    private _registerUpload(newFiles) {
        var fileNames = _(newFiles).pluck('name');
        var url = '/api/experiments/' + this._$stateParams.experimentid +
            '/acquisitions/' + this.id + '/upload/register';
        this.status = 'WAITING';
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $http.post(url, { files: fileNames })
        .then((resp) => {
            // this.clearFiles();
            return resp.status === 200;
        })
        .catch((resp) => {
            return $q.reject(resp.data.error);
        });
    }

    /**
     * Cancel the upload of certain files.
     */
    cancelAllUploads(files) {
        this.clearFiles();
        files.forEach((f) => {
            if (f.upload !== undefined) {
                f.upload.abort();
            }
        });
    }

    /**
     * Upload an array of files.
     */
    uploadFiles(newFiles) {
        var $q = $injector.get<ng.IQService>('$q');
        return this._registerUpload(newFiles)
        .then(() => {
            var promises = this._uploadRegisteredFiles(newFiles);
            return $q.all(promises).then((files) => {
                var allFilesUploaded = _.chain(files).map((f: any) => {
                    return f.status === 'COMPLETE';
                }).all().value();
                if (allFilesUploaded) {
                    this.status = 'COMPLETE';
                }
                return allFilesUploaded;
            });
        });
    }
}
