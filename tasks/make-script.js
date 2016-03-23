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

    /**
     * Compile all TypeScript code and concatenate all library code.
     */
    gulp.task('make-script', function() {
        var src = tsProject.src()
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
            .pipe(banner(opt.banner))
            .pipe(sourcemaps.write('.'))
            .pipe(gulp.dest(opt.destFolder))
            .pipe(_if(opt.prod, rev.manifest()))
            .pipe(_if(opt.prod, rename('rev-manifest-script.json')))
            .pipe(gulp.dest(opt.destFolder))
            .pipe(_if(opt.reload, livereload()));

        var libs;
        if (opt.prod) {
            libs = gulp.src(dependencies)
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
            libs = gulp.src(dependencies)
                .pipe(concat('libs.js'))
                .pipe(gulp.dest(opt.destFolder));
        }

        return es.merge(src, libs);
    });
};
