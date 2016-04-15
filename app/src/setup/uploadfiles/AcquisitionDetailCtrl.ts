class AcquisitionDetailCtrl {

    newFiles: string[];

    static $inject = ['acquisition', '$state'];

    constructor(public acquisition: Acquisition, private _$state) {}

    dropFiles(files) {
        _(files).each(function(f) {
            f.status = 'WAITING';
        });
    }

    uploadFiles() {
        if (this.newFiles.length !== 0) {
            this.acquisition.uploadFiles(this.newFiles);
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
