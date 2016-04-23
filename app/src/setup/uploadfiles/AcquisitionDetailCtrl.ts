class AcquisitionDetailCtrl {

    newFiles: MicroscopeFile[] = [];

    static $inject = ['acquisition', '$state', '$http', '$q'];

    constructor(public acquisition: Acquisition, private _$state,
                private _$http, private _$q) {}

    filterValidFiles(files: {name: string;}[]) {
        return this._$http.post('/api/acquisitions/' + this.acquisition.id + '/file-validity-check', {
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
        this.filterValidFiles(files)
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
    }

}


angular.module('tmaps.ui')
.controller('AcquisitionDetailCtrl', AcquisitionDetailCtrl);

// angular.module('ilui')
// .controller('AcquisitionDetailCtrl',
//     ['acquisition', 'uploadService', '$scope', 'FILE_UPLOAD_STATUS',
//     function(acquisition, uploadService, $scope, FILE_UPLOAD_STATUS) {

//     $scope.newFiles = [];

//     $scope.clearFiles = function() {
//         $scope.newFiles.splice(0, $scope.newFiles.length);
//     };

// }]);

// angular.module('ilui')
// .controller('AcquisitionDetailCtrl',
