module.exports = function(gulp, opt) {
    'use strict';

    var del = require('del');

    // Clean old build files
    gulp.task('clean', function() {
        return del([opt.destFolder]);
    });

};
