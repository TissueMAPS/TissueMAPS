module.exports = function (gulp, $) {

    var connect = require('gulp-connect');
    var watch = require('gulp-watch');

    var argv = require('yargs').argv;
    var shouldWatchTypeScriptFiles = argv['watch-ts'] == true;

    // Watch Files For Changes
    gulp.task('watch', function() {
        if (shouldWatchTypeScriptFiles) {
            gulp.watch('app/src/**/*.ts', ['make-script']);
        }
        gulp.watch('app/src/**/*.js', ['make-script']);
        gulp.watch('app/styles/**/*.less', ['make-style']);
        gulp.watch('app/**/*.+(html|png|ico|jpg)', ['copy']);
        watch($.cfg.destFolder + '/**/*').pipe(connect.reload());
    });

};
