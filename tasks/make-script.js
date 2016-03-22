module.exports = function(gulp, $) {

    var sourcemaps = require('gulp-sourcemaps');
    var typescript = require('gulp-typescript');
    var concat = require('gulp-concat');
    var es = require('event-stream');
    var uglify = require('gulp-uglify');
    var gulpif = require('gulp-if');
    var dependencies = require('../dependencies');

    var argv = require('yargs').argv;
    var prod = argv.prod === true;

    var tsProject = typescript.createProject('tsconfig.json');

    gulp.task('make-script', function() {
        var src = tsProject.src()
            .pipe(sourcemaps.init())
            .pipe(typescript({
                outFile: 'script.js',
                target: 'ES5'
            }))
            .js
            .pipe(gulpif(prod, uglify({
                mangle: true,
                compress: true,
                preserveComments: false
            })))
            .pipe(sourcemaps.write('.'))
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
