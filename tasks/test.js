var karma = require('karma');

module.exports = function(gulp, opt) {
    'use strict';

    gulp.task('test', function(done) {
        karma.server.start({
            configFile: __dirname + '/../karma.conf.js',
            singleRun: true
        });
    });

    gulp.task('tdd', function(done) {
        karma.server.start({
            configFile: __dirname + '/../karma.conf.js'
        });
    });

};
