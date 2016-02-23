module.exports = function(gulp, $) {
    'use strict';

    var runSequence = require('run-sequence');

    // Clean old build files
    gulp.task('build-debug', function() {
        runSequence(
            'clean',
            'build-ol-debug',
            'make-style',
            'make-script',
            'copy'
        );
    });

};
