module.exports = function(gulp, opt) {
    'use strict';

    var es = require('event-stream');
    var revReplace = require('gulp-rev-replace');

    gulp.task('copy', function() {
        // Copy all angular templates 
        var s1 = gulp.src('./app/src/**/*.html', {base: './app'})
            .pipe(gulp.dest(opt.destFolder));
        var s2 = gulp.src('./app/templates/**/*.html', {base: './app'})
            .pipe(gulp.dest(opt.destFolder));
        // Copy all images
        var s3 = gulp.src('./app/resources/**/*.+(png|ico|jpg)', {base: 'app'})
            .pipe(gulp.dest(opt.destFolder));
        // Copy fontawesome fonts
        var s4 = gulp.src('./app/assets/libs/bower_components/fontawesome/fonts/*', {
            base: './app/assets/libs/bower_components/fontawesome'
        }).pipe(gulp.dest(opt.destFolder));

        /**
         * If the build runs in dev mode the index should just be copied over
         * to the build directory.
         * Furthermore, all source files should be copied as well such that
         * the source code can be inspected using the debugger.
         */
        var s5;
        if (opt.dev) {
           s5 = gulp.src('./app/index.html', {base: './app'})
               .pipe(gulp.dest(opt.destFolder));
           var s6 = gulp.src('./app/src/**/*.ts', {base: './'})
               .pipe(gulp.dest(opt.destFolder));

            return es.merge(s1, s2, s3, s4, s5, s6);
        /**
         * If the build runs in production mode then we need to
         * replace all references to javascript files in the index with the files
         * that include the revision hash at the end of their name.
         */
        } else {
            // The three revision manifests (i.e. json files that save the mapping of
            // what file belongs to what revved filename) are saved separately for
            // both the two javascript and the one css files.
            // Therefore, rev-replace is called three times.
            var scriptManifest = gulp.src(opt.destFolder + '/rev-manifest-script.json');
            var libsManifest = gulp.src(opt.destFolder + '/rev-manifest-libs.json');
            var styleManifest = gulp.src(opt.destFolder + '/rev-manifest-style.json');
            var scriptManifestJtUI = gulp.src(opt.destFolder + '/rev-manifest-jtui.json');
            var styleManifestJtUI = gulp.src(opt.destFolder + '/rev-manifest-style-jtui.json');
            s5 = gulp.src('./app/index.html')
                .pipe(revReplace({manifest: scriptManifest}))
                .pipe(revReplace({manifest: libsManifest}))
                .pipe(revReplace({manifest: styleManifest}))
                .pipe(revReplace({manifest: scriptManifestJtUI}))
                .pipe(revReplace({manifest: styleManifestJtUI}))
                .pipe(gulp.dest(opt.destFolder));

            return es.merge(s1, s2, s3, s4, s5);
        }

    });

};
