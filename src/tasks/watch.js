module.exports = function (gulp, opt) {

    var livereload = require('gulp-livereload');
    var runSequence  = require('run-sequence');

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
            gulp.watch('app/src/**/*.ts', ['make-script', 'copy']);
        }
        if (opt.watchOl) {
            gulp.watch('app/assets/libs/ol3/src/**/*.js', function() {
                runSequence(['compile-ol-debug', 'make-script']);
            });
        }
        gulp.watch('app/src/**/*.js', ['make-script']);
        gulp.watch('app/assets/jtui/**/*.less', ['make-style']);
        gulp.watch('app/assets/less/**/*.less', ['make-style']);
        gulp.watch('app/assets/css/**/*.css', ['make-style']);
        gulp.watch('app/**/*.+(png|ico|jpg)', ['copy']);
        // Watch the two template directories for changes in html
        gulp.watch('app/src/**/*.+(html)', ['copy']);
        gulp.watch('app/templates/**/*.+(html)', ['copy']);
        gulp.watch('app/index.html', ['copy']);
    });

};
