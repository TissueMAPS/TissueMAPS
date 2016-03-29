module.exports = function(gulp, opt) {
    'use strict';

    var less = require('gulp-less');
    var concat = require('gulp-concat');
    var es = require('event-stream');
    var livereload = require('gulp-livereload');
    var _if = require('gulp-if');
    var rev = require('gulp-rev');
    var rename = require('gulp-rename');
    var banner = require('gulp-banner');

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
            'app/assets/css/jquery-ui.css',
            'app/assets/css/ol.css'
        ]);

        return es.merge(additionalStyles, appStyle)
        .pipe(concat('style.css'))
            // Production
            .pipe(_if(opt.prod, rev()))
            // .pipe(banner(opt.banner))
        .pipe(gulp.dest(opt.destFolder))
            // Production
            .pipe(_if(opt.prod, rev.manifest()))
            .pipe(_if(opt.prod, rename('rev-manifest-style.json')))
            .pipe(gulp.dest(opt.destFolder))
            // Development
            .pipe(_if(opt.reload, livereload()));
    });

};
