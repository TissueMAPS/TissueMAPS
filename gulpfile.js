'use strict';

var gulp = require('gulp'),
    path = require('path'),
    fs = require('fs'),
    taskPath = './tasks/',
    taskList = require('fs').readdirSync(taskPath);

var argv = require('yargs').argv

var debugConfig = {
    destFolder: 'build'
};

var productionConfig = {
    destFolder: 'build'
};

// Choose depending on argv
var cfg = debugConfig;

var $ = {
    pkg: JSON.parse(fs.readFileSync('./package.json')),
    rootDir: path.resolve('.'),
    cfg: cfg
};

taskList.forEach(function(taskFile) {
    // or .call(gulp,...) to run this.task('foobar')...
    require(taskPath + taskFile)(gulp, $);
});

