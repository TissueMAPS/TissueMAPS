module.exports = function(gulp, opt) {

    var sourcemaps = require('gulp-sourcemaps');
    var typescript = require('gulp-typescript');
    var concat = require('gulp-concat');
    var es = require('event-stream');
    var uglify = require('gulp-uglify');
    var _if = require('gulp-if');
    var rev = require('gulp-rev');
    var dependencies = require('../dependencies');
    var rename = require('gulp-rename');
    var livereload = require('gulp-livereload');
    var tsProject = typescript.createProject('tsconfig.json');
    var banner = require('gulp-banner');

    gulp.task('make-test-script', function() {

        var typeDefFiles = gulp.src([
            './app/typedefs/DefinitelyTyped/jasmine/jasmine.d.ts',
            './app/typedefs/DefinitelyTyped/angularjs/angular-mocks.d.ts',
            './app/typedefs/libs.d.ts',
            './app/typedefs/DefinitelyTyped/underscore/underscore.d.ts',
            './app/typedefs/DefinitelyTyped/angularjs/angular.d.ts',
            './app/typedefs/DefinitelyTyped/bluebird/bluebird.d.ts',
            './app/typedefs/DefinitelyTyped/jquery/jquery.d.ts',
            './app/typedefs/DefinitelyTyped/openlayers/openlayers.d.ts',
            opt.destFolder + '/script.d.ts'
        ]);
        var testFiles = gulp.src('./test/unit/**/*.ts');
        es.merge(typeDefFiles, testFiles)
            .pipe(typescript({
                outFile: 'script.test.js',
                target: 'ES5'
            }))
            .pipe(gulp.dest(opt.destFolder));
    });

    /**
     * Compile all TypeScript code and concatenate all library code.
     */
    gulp.task('make-script', function() {
        /**
         * Copy the typescript files into the directory from which the connect
         * server serves its files. By doing so the original sources files can be
         * loaded by the browser when interacting with the source map.
         */
        var copy;
        if (opt.dev) {
            var copyTs = gulp.src('./app/src/**/*.ts', {base: './app'})
                .pipe(gulp.dest(opt.destFolder));
            var copyJs = gulp.src('./app/src/**/*.js', {base: './app'})
                .pipe(gulp.dest(opt.destFolder));
            copy = es.merge(copyTs, copyJs);
        }

        // Only produce declaration files in case of dev mode.
        tsProject.config.declaration = opt.dev;

        /**
         * Compile the application code.
         * In case of production execution mode the source code will be
         * uglified and revved.
         *
         * The application code is built in two stages: first, all source code
         * that is written in TypeScript is compiled and uglified etc.
         * Second, all JavaScript code (mainly JtUI) is concatenated and
         * similarly uglified/revved/etc.
         */
        var tsSrc = tsProject.src()
            .pipe(sourcemaps.init())
            .pipe(typescript({
                outFile: 'script.js',
                target: 'ES5'
            }))
            .js
            .pipe(_if(opt.prod,
                uglify({
                    mangle: true,
                    compress: true,
                    preserveComments: {
                        license: true
                    }
                })
            ))
            .pipe(_if(opt.prod, rev()))
            .pipe(_if(opt.prod, banner(opt.banner)))
            // Produce source maps (won't work with banner)
            .pipe(_if(opt.dev, 
                sourcemaps.write('.', {
                    sourceRoot: '/app/src/'
                })
            ))
            .pipe(gulp.dest(opt.destFolder))
            .pipe(_if(opt.prod, rev.manifest()))
            .pipe(_if(opt.prod, rename('rev-manifest-script.json')))
            .pipe(gulp.dest(opt.destFolder))
            .pipe(_if(opt.reload, livereload()));

        /**
         * Compile the JtUI application source code.
         * In case of production execution mode the source code will be uglified and revved.
         */
        var jsSrc = gulp.src('app/src/**/*.js')
            .pipe(sourcemaps.init())
            .pipe(concat('script-jtui.js'))
            .pipe(_if(opt.prod,
                uglify({
                    mangle: true,
                    compress: true,
                    preserveComments: {
                        license: true
                    }
                })
            ))
            .pipe(_if(opt.prod, rev()))
            .pipe(_if(opt.prod, banner(opt.banner)))
            // Produce source maps (won't work with banner)
            .pipe(_if(opt.dev, 
                sourcemaps.write('.', {
                    sourceRoot: '/app/src/'
                })
            ))
            .pipe(gulp.dest(opt.destFolder))
            .pipe(_if(opt.prod, rev.manifest()))
            .pipe(_if(opt.prod, rename('rev-manifest-jtui.json')))
            .pipe(gulp.dest(opt.destFolder))
            .pipe(_if(opt.reload, livereload()));

        var src = es.merge(jsSrc, tsSrc);

        /**
         * Compile the library code.
         * In case of production mode also apply revving and uglifying.
         */
        var libs;
        if (opt.prod) {
            libs = gulp.src(dependencies.js)
                .pipe(concat('libs.js'))
                .pipe(uglify({
                        mangle: false,
                        compress: false,  // FIXME: if true gulp crashes
                        preserveComments: {
                            license: true
                        }
                    })
                )
                .pipe(rev())
                .pipe(gulp.dest(opt.destFolder))
                .pipe(rev.manifest())
                .pipe(rename('rev-manifest-libs.json'))
                .pipe(gulp.dest(opt.destFolder));
        } else {
            libs = gulp.src(dependencies.js)
                .pipe(concat('libs.js'))
                .pipe(gulp.dest(opt.destFolder));
        }

        if (opt.dev) {
            return es.merge(copy, src, libs);
        } else {
            return es.merge(src, libs);
        }
    });


};
