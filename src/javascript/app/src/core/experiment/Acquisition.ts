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
    description: string;
    status: string;
    experiment_id: string;
}

class Acquisition {
    id: string;
    name: string;
    description: string;
    status: string;
    experimentId: string;
    files: MicroscopeFile[] = [];

    private _uploader: any;

    /**
     * Construct a new acquisition.
     *
     * @class Acquisition
     * @classdesc An acquisition represents a collection of imagefiles and
     * metadata files produced by a single microscope acquisition run.
     * @param {AcquisitionArgs} args - Constructor arguments.
     */
    constructor(args: AcquisitionArgs) {
        this.experimentId = args.experiment_id;
        delete args.experiment_id;
        _.extend(this, args);

        this._uploader = $injector.get<any>('Upload');
        this._uploader.setDefaults({ngfMinSize: 0, ngfMaxSize: 5000000000});
        this._uploader.defaults.blobUrlsMaxQueueSize = 10;  // default: 200
        this._uploader.defaults.blobUrlsMaxMemory = 5000000000;
    }

    fetchExistingFiles(): ng.IPromise<MicroscopeFile[]> {
        this.clearFiles();
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var imageUrl = '/api/experiments/' + this.experimentId +
            '/acquisitions/' + this.id + '/image-files';
        var metaDataUrl = '/api/experiments/' + this.experimentId +
            '/acquisitions/' + this.id + '/metadata-files';
        return $q.all({
            imageFiles: $http.get(imageUrl),
            metaDataFiles: $http.get(metaDataUrl)
        }).then((responses: any) => {
            var imageFiles = responses.imageFiles.data.data.filter((f) => {
                return f.status == 'COMPLETE';
            });
            var metaDataFiles = responses.metaDataFiles.data.data.filter((f) => {
                return f.status == 'COMPLETE';
            });
            var files = Array.prototype.concat(imageFiles, metaDataFiles)
            this.files = files;
            return files;
        });
    }

    /**
     * Upload a mutiple files. This method has to be called after the files
     * have been registered, i.e. created server-side.
     */
    private _uploadRegisteredFiles(newFiles): any {
        var url = '/api/experiments/' + this.experimentId +
            '/acquisitions/' + this.id + '/upload/upload-file';
        var $q = $injector.get<ng.IQService>('$q');
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
        var url = '/api/experiments/' + this.experimentId +
            '/acquisitions/' + this.id + '/upload/register';
        this.status = 'WAITING';
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $http.put(url, { files: fileNames })
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
