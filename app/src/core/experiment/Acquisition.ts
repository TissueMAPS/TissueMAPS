interface SerializedAcquisition {
    id: string;
    name: string;
    description: string;
    plate_id: string;
    microscope_image_files: string[];
    microscope_metadata_files: string[];
}

interface AcquisitionArgs {
    id: string;
    name: string;
    description: string;
    microscopeImageFiles: string[];
    microscopeMetadataFiles: string[];
}

class Acquisition {
    id: string;
    name: string;
    description: string;

    microscopeImageFiles: string[];
    microscopeMetadataFiles: string[];

    status: string = 'WAITING';

    private _uploader: any;

    constructor(args: AcquisitionArgs) {
        _.extend(this, args);

        this._uploader = $injector.get<any>('Upload');
        this._uploader.setDefaults({ngfMinSize: 0, ngfMaxSize: 20000000});
    }

    static fromJSON(aq: SerializedAcquisition) {
        return new Acquisition({
            id: aq.id,
            name: aq.name,
            description: aq.description,
            microscopeImageFiles: aq.microscope_image_files,
            microscopeMetadataFiles: aq.microscope_metadata_files
        });
    }

    static get(id: string) {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.get('/api/acquisitions/' + id)
        .then((resp: {data: {acquisition: SerializedAcquisition;}}) => {
            return Acquisition.fromJSON(resp.data.acquisition);
        })
        .catch((resp) => {
            return resp.data.error;
        })
    }

    static create(plateId: string, args: {name: string; description: string;}) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var def = $q.defer();
        $http.post('/api/plates/' + plateId + '/acquisitions', args)
        .then((resp: {data: {acquisition: SerializedAcquisition}}) => {
            def.resolve(Acquisition.fromJSON(resp.data.acquisition));
        })
        .catch((resp) => {
            def.reject(resp.data.error);
        });
        return def.promise;
    }

    static delete(id: string): ng.IPromise<boolean> {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.delete('/api/acquisitions/' + id)
        .then((resp) => {
            return true;
        })
        .catch((resp) => {
            return resp.data.error;
        });
    }

    private _uploadRegisteredFiles(newFiles) {
        var url = '/api/acquisitions/' + this.id + '/upload-file';
        var $q = $injector.get<ng.IQService>('$q');
        var $window = $injector.get<ng.IWindowService>('$window');
        this.status = 'UPLOADING';
        var filePromises = newFiles.map((f) => {
            var fileDef = $q.defer();
            f.upload = this._uploader.upload({
                url: url,
                header: {'Authorization': 'JWT ' + $window.sessionStorage['token']},
                file: f,
            }).progress((evt) => {
                var progressPercentage = Math.round(100.0 * evt.loaded / evt.total);
                evt.config.file.progress = progressPercentage;
                evt.config.file.status = 'UPLOADING';
            }).success((data, status, headers, config) => {
                config.file.progress = 100;
                config.file.status = 'UPLOADED';
                fileDef.resolve(config.file);
            }).error((data, status, headers, config) => {
                config.file.status = 'FAILED';
                this.status = 'FAILED';
                fileDef.resolve(config.file);
            });
            return fileDef.promise;
        });
        return filePromises;
    }

    private _registerUpload(newFiles) {
        var fileNames = _(newFiles).pluck('name');
        var url = '/api/acquisitions/' + this.id + '/register-upload';
        this.status = 'WAITING';
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $http.put(url, { files: fileNames })
        .then((resp) => {
            return resp.status === 200;
        })
        .catch((resp) => {
            return $q.reject(resp.data.error);
        });
    }

    cancelAllUploads(files) {
        files.forEach((f) => {
            if (f.upload !== undefined) {
                f.upload.abort();
            }
        });
    }

    uploadFiles(newFiles) {
        var $q = $injector.get<ng.IQService>('$q');
        return this._registerUpload(newFiles)
        .then(() => {
            var promises = this._uploadRegisteredFiles(newFiles);
            return $q.all(promises).then((files) => {
                var allFilesUploaded = _.chain(files).map((f: any) => {
                    console.log('File uploaded:' , f);
                    return f.status === 'UPLOADED';
                }).all().value();
                if (allFilesUploaded) {
                    this.microscopeImageFiles = <string[]> _.pluck(files, 'name');
                    console.log('All files uploaded:' , f);
                    this.status = 'COMPLETE';
                }
                return allFilesUploaded;
            });
        });
    }

}
