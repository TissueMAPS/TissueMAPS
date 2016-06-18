/**
 * A file that was produced by a microscope. This can be a metadata file or
 * an image file.
 */
interface MicroscopeFile {
    name: string;
    upload_status: string;
}

/**
 * Constructor arguments for an acquisition.
 */
interface AcquisitionArgs {
    id: string;
    name: string;
    description: string;
    status: string;
}

class Acquisition {
    id: string;
    name: string;
    description: string;
    status: string;
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
        _.extend(this, args);

        this._uploader = $injector.get<any>('Upload');
        this._uploader.setDefaults({ngfMinSize: 0, ngfMaxSize: 20000000});
        this._uploader.defaults.blobUrlsMaxQueueSize = 10;  // default: 200
        this._uploader.defaults.blobUrlsMaxMemory = 20000000;
    }

    fetchExistingFiles(): ng.IPromise<MicroscopeFile[]> {
        this.clearFiles();
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $q.all({
            imageFiles: $http.get('/api/acquisitions/' + this.id + '/image_files'),
            metaDataFiles: $http.get('/api/acquisitions/' + this.id + '/metadata_files')
        }).then((responses: any) => {
            var imageFiles = responses.imageFiles.data.data.filter((f) => {
                return f.upload_status == 'COMPLETE';
            });
            var metaDataFiles = responses.metaDataFiles.data.data.filter((f) => {
                return f.upload_status == 'COMPLETE';
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
    private _uploadRegisteredFiles(newFiles) {
        var url = '/api/acquisitions/' + this.id + '/upload-file';
        var $q = $injector.get<ng.IQService>('$q');
        var $window = $injector.get<ng.IWindowService>('$window');
        this.status = 'UPLOADING';
        var namesUploadedFiles = this.files.map(function(f) {
            return f.name;
        });
        var filePromises = newFiles.map((newFile) => {
            var fileDef = $q.defer();
            if (namesUploadedFiles.indexOf(newFile.name) != -1) {
                // Skip files that were already uploaded.
                newFile.progress = 100;
                newFile.status = 'COMPLETE';
                fileDef.resolve(newFile);
            } else {
                newFile.upload = this._uploader.upload({
                    url: url,
                    header: {'Authorization': 'JWT ' + $window.sessionStorage['token']},
                    file: newFile,
                }).progress((evt) => {
                    var progressPercentage = Math.round(100.0 * evt.loaded / evt.total);
                    evt.config.file.progress = progressPercentage;
                    evt.config.file.status = 'UPLOADING';
                }).success((data, status, headers, config) => {
                    // console.log('upload of file complete: ', config.file.name)
                    config.file.progress = 100;
                    config.file.status = 'COMPLETE';
                    this.files.push(<MicroscopeFile>{
                        name: config.file.name, upload_status: 'COMPLETE'
                    });
                    fileDef.resolve(config.file);
                }).error((data, status, headers, config) => {
                    console.log('upload of file failed: ', config.file.name)
                    config.file.status = 'FAILED';
                    this.status = 'FAILED';
                    fileDef.resolve(config.file);
                });
            }
            return fileDef.promise;
        });
        return filePromises;
    }

    /**
     * Clear all files on this object (only client-side).
     */
    clearFiles() {
        this.files.splice(0, this.files.length);
    }

    countCompleted() {
        return this.files.filter((f) => {
            return f.upload_status == 'COMPLETE';
        }).length
    }
    /**
     * Register files to be uploaded. This will create server-side
     * objects for all the files. Only files that were registered can be 
     * uploaded.
     */
    private _registerUpload(newFiles) {
        var fileNames = _(newFiles).pluck('name');
        var url = '/api/acquisitions/' + this.id + '/register-upload';
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
