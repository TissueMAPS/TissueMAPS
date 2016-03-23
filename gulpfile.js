'use strict';

// Include gulp itself
var gulp = require('gulp');
var argv = require('yargs').argv;
var pkg = require('./package.json');
var template = require('es6-template-strings');

var banner = template([
  '/**',
  ' * ${pkg.name} - ${pkg.description}',
  ' * @version ${pkg.version}',
  ' * @author ${pkg.author}',
  ' * @homepage ${pkg.homepage}',
  ' * @license ${pkg.license}',
  ' */',
  ''].join('\n'), {
      pkg: pkg
});

// Define variables
var opt = {
    destFolder: './build',
    prod: argv.prod === true,
    dev: argv.prod !== true,
    watchTs: argv['watch-ts'] === true,
    reload: argv.reload === true,
    banner: banner
};

// Read tasks
var taskPath = './tasks';
var taskList = require('fs').readdirSync(taskPath);

taskList.forEach(function(taskFile) {
    require(taskPath + '/' + taskFile)(gulp, opt);
});

gulp.task('default', ['dev']);
