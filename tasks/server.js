module.exports = function(gulp, $) {
    'use strict';

    var connect = require('gulp-connect');
    var proxy = require('http-proxy-middleware');

    gulp.task('server', function() {
        connect.server({
            port: 8002,
            root: 'build',
            livereload: 35761,
            middleware: function(connect, opt) {
                return [
                    proxy('/api', {
                        target: 'http://localhost:5002',
                        changeOrigin: false
                    }),
                    proxy('/auth', {
                        target: 'http://localhost:5002',
                        changeOrigin: false
                    })
                ];
            }
        });
    });
};
