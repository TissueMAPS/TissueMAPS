module.exports = function(gulp, $) {
    'use strict';

    var del = require('del');

    // Clean old build files
    gulp.task('clean', function() {
        return del(['build']);
    });

};
