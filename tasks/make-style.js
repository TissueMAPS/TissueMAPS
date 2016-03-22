module.exports = function(gulp, $) {
    'use strict';

    var less = require('gulp-less');
    var rename = require('gulp-rename');
    var concat = require('gulp-concat');
    var es = require('event-stream');

    // Compile LESS files
    gulp.task('make-style', function() {
        var appStyle = gulp.src([
            'app/assets/less/style.less'
        ])
        .pipe(less());

        var additionalStyles = gulp.src([
            'app/assets/libs/unmanaged/ng-color-picker/color-picker.css',
            'app/assets/libs/bower_components/perfect-scrollbar/css/perfect-scrollbar.css',
            'app/assets/libs/bower_components/fontawesome/css/font-awesome.css',
            'app/assets/css/jquery-ui.css'
        ]);

        return es.merge(additionalStyles, appStyle)
        .pipe(concat('style.css'))
        .pipe(gulp.dest($.cfg.destFolder));
    });

};
