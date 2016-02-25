'use strict';

var gulp = require('gulp'),
    path = require('path'),
    fs = require('fs'),
    taskPath = './tasks/',
    taskList = require('fs').readdirSync(taskPath);

var $ = {
    pkg: JSON.parse(fs.readFileSync('./package.json')),
    rootDir: path.resolve('.')
};

taskList.forEach(function(taskFile) {
    require(taskPath + taskFile)(gulp, $);
});


var runSequence = require('run-sequence');

gulp.task('default', function() {
    return runSequence('build', 'server');
});
