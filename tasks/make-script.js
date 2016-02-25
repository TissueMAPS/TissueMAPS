module.exports = function(gulp, $) {
    'use strict';

    var sourcemaps = require('gulp-sourcemaps');
    var typescript = require('gulp-typescript');
    var wiredep = require('wiredep');
    var concat = require('gulp-concat');
    var es = require('event-stream');
    var uglify = require('gulp-uglify');
    var gulpif = require('gulp-if');

    var argv = require('yargs').argv;
    var prod = argv.prod == true;

    gulp.task('make-script', function() {
        var sourceTsFiles = [
            // Source files
            'app/src/**/*.ts',
            // External type definitions
            'app/typedefs/DefinitelyTyped/underscore/underscore.d.ts',
            'app/typedefs/DefinitelyTyped/angularjs/angular.d.ts',
            'app/typedefs/DefinitelyTyped/jquery/jquery.d.ts',
            'app/typedefs/DefinitelyTyped/openlayers/openlayers.d.ts'
        ];
         
        var tsResult = gulp.src(sourceTsFiles)
            .pipe(sourcemaps.init())
            .pipe(typescript({
                outFile: 'script.js',
                target: 'ES5'
            }));

        var dependencies = wiredep().js;
        Array.prototype.push.apply(dependencies, [
            'app/assets/libs/unmanaged/jquery-ui.min.js',
            'app/assets/libs/unmanaged/angular-perfect-scrollbar.js',
            'app/assets/libs/ol-debug.js'
            // 'app/assets/libs/unmanaged/ng-color-picker/color-picker.js',
        ]);

        var src = tsResult.js
            .pipe(gulpif(!prod, sourcemaps.write('.')))
            .pipe(gulpif(prod, uglify({
                mangle: true,
                compress: true,
                preserveComments: false
            })))
            .pipe(gulp.dest('build'));

        var libs = gulp.src(dependencies)
            .pipe(concat('libs.js'))
            .pipe(gulpif(prod, uglify({
                mangle: false,
                compress: false,  // FIXME: if true gulp crashes
                preserveComments: {
                    license: true
                }
            })))
            .pipe(gulp.dest('build'));

        return es.merge(src, libs);
    });
};
