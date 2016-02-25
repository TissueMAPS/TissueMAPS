module.exports = function(gulp, $) {
    'use strict';

    var es = require('event-stream');

    gulp.task('copy', function() {
        var s1 = gulp.src('./app/src/**/*.html', {base: './app/src'})
            .pipe(gulp.dest('build'));
        var s2 = gulp.src('./app/resources/**/*.+(png|ico)', {base: './app'})
            .pipe(gulp.dest('build'));

        return es.merge(s1, s2);
    });

};
