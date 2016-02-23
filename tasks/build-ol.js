module.exports = function(gulp, $) {
    'use strict';

    var exec = require('child_process').exec;
    var olDir = 'app/assets/libs/ol3';

    gulp.task('build-ol', function(cb) {
        exec('(node ' + olDir + '/tasks/build.js ' + olDir + '/config/ol.json app/assets/libs/ol.js)',
             function(err, stdout, stderr) {

            console.log(stdout);
            console.log(stderr);
            cb(err);
        });
    });

    gulp.task('build-ol-debug', function(cb) {
        exec('(node ' + olDir + '/tasks/build.js ' + olDir + '/config/ol-debug.json app/assets/libs/ol-debug.js)',
             function(err, stdout, stderr) {
            console.log(stdout);
            console.log(stderr);
            cb(err);
        });
    });

    gulp.task('init-ol', function(cb) {
        exec('(cd ' + olDir + ' && make install)', function(err, stdout, stderr) {
            console.log(stdout);
            console.log(stderr);
            cb(err);
        });
    });

};
