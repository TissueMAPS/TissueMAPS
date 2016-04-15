 var dependencies = [
    /* JQuery and JQuery-UI */
    'bower_components/jquery/dist/jquery.js',
    // JQuery-UI needs ot come before Angular due to a bug that occurs
    // otherwise hen removing a slider
    'unmanaged/jquery-ui.min.js',
    /* Underscore */
    'bower_components/underscore/underscore.js',
    /* Custom openlayers 3 version */
    'ol-debug.js',
    /* Angular */
    'bower_components/angular/angular.js',
    'bower_components/angular-ui-router/release/angular-ui-router.js', 
    'bower_components/angular-sanitize/angular-sanitize.js', 
    /* Angular UI */
    'bower_components/angular-ui-sortable/sortable.min.js',
    'bower_components/angular-ui-slider/src/slider.js',
    'bower_components/angular-ui-bootstrap-bower/ui-bootstrap-tpls.js',
    /* Other plugins */
    'unmanaged/ng-color-picker/color-picker.js',
    'bower_components/perfect-scrollbar/js/min/perfect-scrollbar.jquery.min.js',
    // I made some small changes to the following file since it had some bugs
    // on the pull requests weren't accepted on the original repo
    'unmanaged/angular-perfect-scrollbar.js',
    'bower_components/momentjs/moment.js',
    'bower_components/ng-websocket/ng-websocket.js',
    'bower_components/ng-file-upload/ng-file-upload.min.js',
    'bower_components/angular-ui-router-breadcrumbs/dist/angular-ui-router-breadcrumbs.min.js'
];

module.exports = dependencies.map(function(path) {
    return 'app/assets/libs/' + path;
});
