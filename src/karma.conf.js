module.exports = function(config) {
    var appSources = ['build/script.js'];
    var libSources = ['build/libs.js'];
    var testSources = [
        'test/unit/**/*.js',
        'build/script.test.js'
    ];
    var sourceFiles = Array.prototype.concat(
        libSources,
        appSources,
        ['app/assets/libs/bower_components/angular-mocks/angular-mocks.js'],
        testSources
    );

    config.set({
        frameworks: ['jasmine'],
        captureConsole: true,
        browsers: ['PhantomJS'],
        reporters: 'mocha',
        files: sourceFiles
    });
};
