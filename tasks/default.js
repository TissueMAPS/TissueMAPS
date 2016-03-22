module.exports = function(gulp, $) {
    'use strict';

    var runSequence = require('run-sequence');

    gulp.task('default', function() {
        return runSequence(
            // Clean old build files
            'clean',
            // 'compile-ol-debug',
            ['make-script', 'make-style'], 
            'copy',
            'watch',
            'start-server'
        );
    });

};
