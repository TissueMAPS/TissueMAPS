module.exports = function(gulp, $) {
    'use strict';

    gulp.task('copy', function() {
        gulp.src('./app/src/**/*.html', {base: './app/src'})
            .pipe(gulp.dest('build'));
        gulp.src('./app/resources/**/*.+(png|ico)', {base: './app'})
            .pipe(gulp.dest('build'));
    });

};
