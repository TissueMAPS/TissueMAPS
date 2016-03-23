module.exports = function(gulp, opt) {
    'use strict';

    var runSequence = require('run-sequence');

    gulp.task('dev', function() {
        return runSequence(
            'build',
            'watch',
            'start-server'
        );
    });

};
