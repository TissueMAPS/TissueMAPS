var argv = require('yargs').argv;

module.exports = function(gulp, opt) {
    'use strict';

    var runSequence = require('run-sequence');

    if (opt.prod) {
        console.log('PRODUCTION BUILD');
    }
    gulp.task('build', function() {
        return runSequence(
            'clean',
            // 'compile-ol-debug',
            ['make-script', 'make-style'], 
            'copy'
        );
    });

};
