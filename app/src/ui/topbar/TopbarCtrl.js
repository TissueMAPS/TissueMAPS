angular.module('tmaps.ui')
.controller('TopbarCtrl', ['application', 'openlayers', '$modal', '$http', 'appstateService', '$q',
    function(application, ol, $modal, $http, appstateService, $q) {

    var self = this;

    this.appstateService = appstateService;

    var mapControls = [
        new ol.control.Zoom(),
        new ol.control.FullScreen(),
        new ol.control.ZoomToExtent()
    ];

    mapControls.forEach(function(ctrl) {
        // application.get().addControl(ctrl);
    });
}]);
