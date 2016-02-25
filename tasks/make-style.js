module.exports = function(gulp, $) {
    'use strict';

    var less = require('gulp-less');
    var rename = require('gulp-rename');
    var es = require('event-stream');

    // Compile LESS files
    gulp.task('make-style', function() {
        var s1 = gulp.src([
            'app/assets/less/main/style.less'
        ])
        .pipe(less())
        .pipe(rename('style-main.css'))
        .pipe(gulp.dest($.cfg.destFolder));

        var s2 = gulp.src([
            'app/assets/less/tools/style.less'
        ])
        .pipe(less())
        .pipe(rename('style-tools.css'))
        .pipe(gulp.dest($.cfg.destFolder));

        return es.merge(s1, s2);
    });

};
