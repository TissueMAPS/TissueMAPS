module.exports = function(gulp, $) {
    'use strict';

    var less = require('gulp-less');
    var rename = require("gulp-rename");

    // Compile LESS files
    gulp.task('make-style', function() {
        gulp.src([
            'app/assets/less/main/style.less'
        ])
        .pipe(less())
        .pipe(rename('style-main.css'))
        .pipe(gulp.dest($.cfg.destFolder));

        return gulp.src([
            'app/assets/less/tools/style.less'
        ])
        .pipe(less())
        .pipe(rename('style-tools.css'))
        .pipe(gulp.dest($.cfg.destFolder));
    });

};
