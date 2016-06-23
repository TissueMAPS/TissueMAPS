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
var isProd = argv.prod === true;
var isDev = !isProd;
var opt = {
    destFolder: './build',
    prod: isProd,
    dev: isDev,
    watchTs: isDev,
    reload: isDev,
    banner: banner,
    watchOl: isDev
};

// Read tasks
var taskPath = './tasks';
var taskList = require('fs').readdirSync(taskPath);

taskList.forEach(function(taskFile) {
    require(taskPath + '/' + taskFile)(gulp, opt);
});

gulp.task('default', ['dev']);
