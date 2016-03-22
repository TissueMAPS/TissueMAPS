'use strict';

// Include gulp itself
var gulp = require('gulp');
var runSequence = require('run-sequence');

// Define variables
var config = {
    destFolder: './build' 
};

// Read tasks
var taskPath = './tasks';
var taskList = require('fs').readdirSync(taskPath);

taskList.forEach(function(taskFile) {
    var $ = {
        cfg: config
    };
    require(taskPath + '/' + taskFile)(gulp, $);
});
