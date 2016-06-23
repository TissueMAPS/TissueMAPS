module.exports = function(gulp, opt) {
    'use strict';

    var less = require('gulp-less');
    var concat = require('gulp-concat');
    var es = require('event-stream');
    var livereload = require('gulp-livereload');
    var _if = require('gulp-if');
    var rev = require('gulp-rev');
    var rename = require('gulp-rename');
    var dependencies = require('../dependencies');

    // Compile LESS files
    gulp.task('make-style', function() {
        var appStyle = gulp.src([
            'app/assets/less/style.less'
        ])
        .pipe(less());
        var additionalStyles = gulp.src(dependencies.css);
        appStyle = es.merge(additionalStyles, appStyle)
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

        var jtuiStyle = gulp.src([
            'app/assets/jtui/style.less'
        ])
        .pipe(less())
        .pipe(rename('style-jtui.css'))
            // Production
            .pipe(_if(opt.prod, rev()))
            // .pipe(banner(opt.banner))
        .pipe(gulp.dest(opt.destFolder))
            // Production
            .pipe(_if(opt.prod, rev.manifest()))
            .pipe(_if(opt.prod, rename('rev-manifest-style-jtui.json')))
            .pipe(gulp.dest(opt.destFolder))
            // Development
            .pipe(_if(opt.reload, livereload()));

        return es.merge(appStyle, jtuiStyle);
    });
};
