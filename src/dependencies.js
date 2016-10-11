 var dependencies = {
    js: [
        /**
         * TissueMAPS
         */
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
        'bower_components/angular-animate/angular-animate.min.js',
        'bower_components/angular-boostrap/ui-bootstrap.min.js',
        'bower_components/angular-bootstrap/ui-bootstrap-tpls.min.js',
        // 'bower_components/angular-ui-bootstrap-bower/ui-bootstrap-tpls.js',
        /* Other plugins */
        'unmanaged/ng-color-picker/color-picker.js',
        'bower_components/perfect-scrollbar/js/min/perfect-scrollbar.jquery.min.js',
        // I made some small changes to the following file since it had some bugs
        // on the pull requests weren't accepted on the original repo
        'unmanaged/angular-perfect-scrollbar.js',
        'bower_components/momentjs/moment.js',
        'bower_components/ng-websocket/ng-websocket.js',
        'bower_components/ng-file-upload/ng-file-upload.min.js',
        'bower_components/angular-ui-router-breadcrumbs/dist/angular-ui-router-breadcrumbs.min.js',
        'bower_components/plotlyjs/plotly.js',
        'bower_components/angular-ui-scroll/dist/ui-scroll.min.js',

        /**
         * JtUI
         */
        'bower_components/js-yaml/dist/js-yaml.min.js',
        'bower_components/perfect-scrollbar/js/perfect-scrollbar.jquery.min.js',
        'bower_components/angular-loading-bar/build/loading-bar.min.js',
        'bower_components/angular-hotkeys/build/hotkeys.min.js',
        'bower_components/highlightjs/highlight.pack.min.js',
        // 'bower_components/angular-highlightjs/angular-highlightjs.min.js',
        'bower_components/marked/lib/marked.js',
        'bower_components/angular-marked/dist/angular-marked.min.js',
        'bower_components/checklist-model/checklist-model.js',
        'bower_components/angular-xeditable/dist/js/xeditable.min.js',
        'bower_components/ng-websocket/ng-websocket.js',
        'bower_components/angular-smart-table/dist/smart-table.min.js',
        'bower_components/angular-plotly/src/angular-plotly.js',
        'bower_components/EaselJS/lib/easeljs-0.8.2.combined.js',
        'bower_components/ngDraggable/ngDraggable.js'
    ].map(function(path) {
        return 'app/assets/libs/' + path;
    }),
    css: [
        /**
         * TissueMAPS
         */
        'libs/unmanaged/ng-color-picker/color-picker.css',
        'libs/bower_components/perfect-scrollbar/css/perfect-scrollbar.css',
        'libs/bower_components/fontawesome/css/font-awesome.css',
        'css/jquery-ui.css',
        'css/ol.css',
        /**
         * JtUI
         */
        'bower_components/angular-loading-bar/build/loading-bar.min.css',
        'bower_components/angular-hotkeys/build/hotkeys.min.css',
        // 'bower_components/highlightjs/styles/solarized-dark.css'
    ].map(function(path) {
        return 'app/assets/' + path;
    })
};

module.exports = dependencies;
