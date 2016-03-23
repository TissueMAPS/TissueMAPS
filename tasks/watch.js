module.exports = function (gulp, opt) {

    var livereload = require('gulp-livereload');

    // Watch Files For Changes
    gulp.task('watch', function() {
        if (opt.reload) {
            livereload.listen({
                basepath: 'build'
            });
        }
        /*
         * TypeScript files can also be watched for changes. This is
         * optional since some people might want to use compilation tools
         * from within their editor/IDE.
         */
        if (opt.watchTs) {
            gulp.watch('app/src/**/*.ts', ['make-script']);
        }
        gulp.watch('app/src/**/*.js', ['make-script']);
        gulp.watch('app/assets/less/**/*.less', ['make-style']);
        gulp.watch('app/assets/css/**/*.css', ['make-style']);
        gulp.watch('app/**/*.+(png|ico|jpg)', ['copy']);
        // Watch the two template directories for changes in html
        gulp.watch('app/src/**/*.+(html)', ['copy']);
        gulp.watch('app/templates/**/*.+(html)', ['copy']);
        // The index has to be watched separately since it needsto be
        // rev-replaced. This will also take care of the copying.
        gulp.watch('app/index.html', ['rev-replace-index']);
    });

};
