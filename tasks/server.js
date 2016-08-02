module.exports = function(gulp, opt) {
    'use strict';

    var connect = require('gulp-connect');
    var livereload = require('gulp-livereload');
    var proxy = require('http-proxy-middleware');

    gulp.task('start-server', function() {
        connect.server({
            port: 8002,
            root: 'build',
            livereload: opt.reload,
            src: 'http://localhost:35729/livereload.js?snipver=1',
            middleware: function(connect, options) {
                return [
                    proxy('/api', {
                        target: 'http://localhost:5002',
                        changeOrigin: false
                    }),
                    proxy('/auth', {
                        target: 'http://localhost:5002',
                        changeOrigin: false
                    }),
                    proxy('/jtui', {
                        target: 'http://localhost:5002',
                        changeOrigin: false
                    })
                ];
            }
        });
    });
};
