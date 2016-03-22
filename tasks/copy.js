module.exports = function(gulp, $) {
    'use strict';

    var es = require('event-stream');

    gulp.task('copy', function() {
        // Copy main index file
        var s1 = gulp.src('./app/index.html', {base: 'app'})
            .pipe(gulp.dest('build'));

        // Copy all angular templates 
        var s2 = gulp.src('./app/src/**/*.html', {base: './app'})
            .pipe(gulp.dest('build'));
        var s3 = gulp.src('./app/templates/**/*.html', {base: './app'})
            .pipe(gulp.dest('build'));

        // Copy all images
        var s4 = gulp.src('./app/resources/**/*.+(png|ico|jpg)', {base: 'app'})
            .pipe(gulp.dest('build'));

        // Copy fontawesome fonts
        var s5 = gulp.src('./app/assets/libs/bower_components/fontawesome/fonts/*', {
            base: './app/assets/libs/bower_components/fontawesome'
        }).pipe(gulp.dest('build'));

        return es.merge(s1, s2, s3, s4, s5);
    });

};
