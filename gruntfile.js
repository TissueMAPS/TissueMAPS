/**
 * TissueMAPS build script
 * =======================
 *
 * This file defines various tasks for the task runner `grunt` that are needed
 * for building the project, or that help during development.
 *
 * There are two possible tasks that can be executed from the command line:
 *
 *      $ grunt [dev]
 *
 *      will watch files for change and automatically compile them (specyfing 'dev' is optional).
 *      It will also autoreload the browser as soon as the CSS or the Script files change.
 *
 *
 *      $ grunt prod
 *
 *      will create a release build in the directory specified by the PRODUCTION_DIR variable.
 *
 *
 *      $ grunt test
 *
 *      will start a continous testing cycle.
 *
 *
 *
 *  New tasks should be installed with:
 *
 *      $ cd /path/to/tissueMAPS
 *      $ npm install grunt-sometask --save-dev
 */

var path = require('path');

module.exports = function(grunt) {
    'use strict';

    // Execute 'grunt.loadNpmTasks' for all tasks in package.json
    require('load-grunt-tasks')(grunt);
    // Needs to be loaded separately to log execution times
    require('time-grunt')(grunt);

    // Project configuration
    grunt.initConfig({

        // Gives access to the project name and its version number
        pkg: grunt.file.readJSON('package.json'),

        /*
         * VARIABLES
         * ---------
         *
         * These variables define the location of all the directories that hold
         * the source files which need to be processed and ultimately put into
         * the 'dist' directory.
         */

        // Absolute path of client root directory
        ROOT_DIR: path.resolve('.'),

        // Styles
        LESS_DIR: 'styles/less',   // need to be compiled
        CSS_DIR: 'styles/css',    // does not need to be compiled

        // Temp dir where tasks should put intermediate files
        TMP_DIR: '.tmp',

        // Where to place all files when the app is built for production
        PRODUCTION_DIR: 'dist',

        // Where to place the compiled files
        BUILD_DIR: 'build',

        OL_DIR: 'ol3',

        // TODO: Specify license
        // A banner that will be added to the minified files.
        banner: [
            '/*',
            '* Project: <%= pkg.name %>',
            '* Version: <%= pkg.version %> (<%= grunt.template.today("yyyy-mm-dd") %>)',
            '* Author: <%= pkg.author %>',
            '* License: BSD 3',
            '* Copyright(c): <%= grunt.template.today("yyyy") %>',
            '*/'
        ],

        /**
         * TASK CONFIGURATION
         * ------------------
         *
         * Configuration of the tools that need to be executed in order to
         * correctly build the project.
         * Most tasks are configured like this:
         *
         * taskName: {
         *     options: {
         *         ... // task-wide options
         *     },
         *     target1: {
         *         ... // options for target1
         *     },
         *     target2: {
         *         ... // options for target2
         *     }
         * }
         *
         * target1 and target2 are subtasks that can be accessed by
         * taskName:target1 or taskName:target2
         */

        /**
         * Delete content of build directory
         */
        clean: {
            prod: ['<%= PRODUCTION_DIR %>'],
            build: ['<%= BUILD_DIR %>'],
            tmp: ['<%= TMP_DIR %>']
        },

        /**
         * Copy the html and image files into the build directory
         */
        copy: {
            prod: {
                files: [
                    {expand: true, src: ['templates/**/*.html'], dest: '<%= PRODUCTION_DIR %>/'},
                    {'<%= PRODUCTION_DIR %>/index.html': 'index.html'},
                    {'<%= PRODUCTION_DIR %>/style-tools.css': '<%= BUILD_DIR %>/style-tools.css'},
                    {'<%= PRODUCTION_DIR %>/style-main.css': '<%= BUILD_DIR %>/style-main.css'},
                    {expand: true, src: ['resources/**'], dest: '<%= PRODUCTION_DIR %>/'}
                ]
            },
            olSource: {
                files: {
                    'libs/unmanaged/': '<%= OL_DIR %>/build/ol.js'
                }
            }
        },

        /**
         * Prepends the banner to the minified files.
         */
        usebanner: {
            dist: {
                options: {
                    position: 'top',
                    banner: '<%= banner.join("\\n") %>',
                    linebreak: true
                },
                files: {
                    src: [
                        '<%= PRODUCTION_DIR %>/script-main.min.js',
                        '<%= PRODUCTION_DIR %>/script-tools.min.js',
                        '<%= PRODUCTION_DIR %>/style-tools.min.css',
                        '<%= PRODUCTION_DIR %>/style-main.min.css'
                    ]
                }
            }
        },

        /*
         * Expand all glob patterns in script and style tags.
         */
        includeSource: {
            options: {
                templates: {
                    html: {
                        js: '<script src="/{filePath}"></script>'
                    }
                }
            },
            main: {
                files: {
                    'index.html': 'index.pre.html'
                }
            },
            tools: {
                // basePath: '../../',
                files: {
                    'templates/tools/index.html': 'templates/tools/index.pre.html'
                }
            }
        },

        /*
         * The useminPrepare part of the usemin plugin looks at the html file and checks for a build:js or build:css code block.
         * It will take those files found in the code block(s) and concat them together and then runs uglify for js and/or cssmin for css files.
         * useminPrepare requires grunt-contrib-uglify, grunt-contrib-concat, and grunt-contrib-cssmin plugins to be installed. Which is listed in the package.json file.
         *
         * The usemin part will remove the code block(s) and replace that area with the single file path in the html file.
         */
        useminPrepare: {
            html: [
                'index.html',
                'templates/tools/index.html'
            ],
            options: {
                dest: '<%= PRODUCTION_DIR %>'
            }
        },
        usemin: {
            html: [
                '<%= PRODUCTION_DIR %>/index.html',
                '<%= PRODUCTION_DIR %>/templates/tools/index.html'
            ],
            options: {
                assetDirs: [
                    '<% PRODUCTION_DIR %>',
                    '<% PRODUCTION_DIR %>/resources',
                    '<% PRODUCTION_DIR %>/resources/img'
                ]
            }

        },

        /**
         * Compute a hash for each of the listed files and append it to the file's name.
         * Usemin will then replace the standard filename with the new one.
         * By doing this, altering a file will alter its filename and therefore avoid problems with cached, old files.
         */
        filerev: {
            dist: {
                src: [
                    '<%= PRODUCTION_DIR %>/resources/img/**/*.{jpg,png,gif,ico}',
                    '<%= PRODUCTION_DIR %>/**/*.{js,css}'
                ]
            },
        },

        /*
         * Watch files for changes and execute other tasks.
         */
        watch: {
            // Preprocess html files as soon as one changes
            htmlPre: {
                files: ['templates/tools/index.pre.html', 'index.pre.html'],
                tasks: ['includeSource']
            },

            // Auto-reload browser when a html changes
            html: {
                options: { livereload: true },
                files: [
                    'index.html',
                    'templates/**/*.html',
                    '!templates/tools/index.pre.html' // needs to be globbed first
                ]
            },

            // Automatically compile less files on change
            less: {
                files: ['<%= LESS_DIR %>/**/*.less'],
                tasks: ['less', 'includeSource']
            },

            js: {
                files: ['src/**/*.js'],
                tasks: ['includeSource', 'test:unit']
            },

            // jsTest: {
            //     files: ['test/**/*.js'],
            //     tasks: ['karma:unit:run', 'karma:midway:run']
            // },

            // NOTE: Enabling this produces some error messages when running 'watch'
            // openlayersSource: {
            //     files: ['<%= OL_DIR %>/**/*.js'],
            //     tasks: [
            //         'exec:buildOL',
            //         'copy:olSource'
            //     ]
            // },

            // Reload grunt (no tasks need to be specified, this is all that's needed)
            grunt: { files: ['gruntfile.js'] }
        },

        /*
         * Execute the python build script for openlayers.
         * This will create the file ol3/build/ol.js.
         * (has to be copied to libs/unmanaged)
         */
        exec: {
            buildOL: '(cd <%= OL_DIR %> && ./build.py build)' // temporarily change working directory
        },

        /*
         * Compile LESS files to CSS
         *
         * Currently, the main application and the tools sub-app have different less files,
         * although they share some rules.
         * They will also have two different minified files.
         */
        less: {
            options: {
                paths: ['<%= LESS_DIR %>'],
                cleancss: false
            },
            compile: {
                files: {
                    // The style.less file imports all other less files
                    '<%= BUILD_DIR %>/style-main.css': '<%= LESS_DIR %>/main/style.less',
                    '<%= BUILD_DIR %>/style-tools.css': '<%= LESS_DIR %>/tools/style.less'
                }
            }
        },

        /**
         * Removes all comments from the production index.html files.
         * It can also remove all whitespace if desired.
         */
        htmlmin: {
            dist: {
                options: {
                    removeComments: true,
                    collapseWhitespace: false
                },
                files: {
                    '<%= PRODUCTION_DIR %>/index.html': '<%= PRODUCTION_DIR %>/index.html',
                    '<%= PRODUCTION_DIR %>/templates/tools/index.html': '<%= PRODUCTION_DIR %>/templates/tools/index.html'
                }
            }
        },

        notify_hooks: {
            options: {
                enabled: true,
                max_jshint_notifications: 5, // maximum number of notifications from jshint output
                success: false,              // whether successful grunt executions should be notified automatically
                duration: 3                  // the duration of notification in seconds, for `notify-send only
            }
        },

        karma: {
            options: {
                frameworks: ['jasmine'],
                browsers: [
                    'PhantomJS'
                    // 'Chrome'
                ],
                singleRun: true,
                files: [
                    // Files to include everywhere
                    // Library code
                    'libs/bower/jquery/dist/jquery.js',
                    'libs/unmanaged/jquery-ui.min.js',
                    'libs/bower/underscore/underscore.js',

                    'libs/unmanaged/ol3/build/ol.js',

                    'libs/bower/angular/angular.js',
                    'libs/bower/angular-mocks/angular-mocks.js',
                    'libs/bower/angular-ui-router/release/angular-ui-router.js',
                    'libs/bower/angular-sanitize/angular-sanitize.js',
                    'libs/bower/highcharts/highcharts.js',
                    'libs/bower/highcharts-ng/dist/highcharts-ng.min.js',
                    'libs/bower/angular-ui-sortable/sortable.min.js',
                    'libs/bower/angular-ui-slider/src/slider.js',
                    'libs/bower/angular-ui-bootstrap-bower/ui-bootstrap-tpls.js',
                    'libs/bower/ng-color-picker/color-picker.js',
                    'libs/bower/perfect-scrollbar/js/perfect-scrollbar.jquery.js',
                    'libs/unmanaged/angular-perfect-scrollbar.js',
                    'libs/bower/ng-websocket/ng-websocket.js',

                    // Module declarations
                    'src/tmaps.shared.js',
                    'src/tmaps.main.js',
                    'src/tmaps.tools.js',

                    // Source
                    'src/shared/**/*.js',
                    'src/main/**/*.js',
                    'src/tools/**/*.js'
                ]
            },
            unit: {
                singleRun: false,
                files: [
                    { src: ['test/unit/**/*.js'] }
                ]
            },
            midway: {
                files: [
                    { src: 'libs/bower/ngMidwayTester/src/ngMidwayTester.js' },
                    { src: ['test/midway/**/*.js'] }
                ]
            },
            e2e: {
                files: [
                    { src: ['test/e2e/**/*.js'] }
                ]
            },
            all: {
                singleRun: false,
                autoWatch: true,
                files: [
                    { src: ['test/unit/**/*.js'] },
                    { src: 'libs/bower/ngMidwayTester/src/ngMidwayTester.js' },
                    { src: ['test/midway/**/*.js'] },
                    { src: ['test/e2e/**/*.js'] }
                ]
            },
            cov: {
                singleRun: true,
                preprocessors: {
                    'src/**/*.js': 'coverage'
                },
                reporters: ['coverage'],
                coverageReporter: {
                    type : 'text',
                    dir : 'coverage/'
                }
            }
        },

        protractor: {
            options: {
                configFile: "test/protractor.conf.js", // Default config file
                // If false, the grunt process stops when the test fails.
                keepAlive: true,
                // If true, protractor will not use colors in its output.
                noColor: false,
                args: {
                    // Arguments passed to the command
                }
            },
            all: {}
        }
    });

    // Necessary when using custom options
    grunt.task.run('notify_hooks');


    /*
     * ALIAS TASKS
     * -----------
     *
     * Tasks that call other tasks.
     */

    // Build for development and watch files for changes.
    grunt.registerTask('dev', [
        'clean:build',
        'clean:tmp',
        'copy:olSource',
        'less',
        'includeSource',

        'watch'
    ]);
    // The dev task is also executed when no task is specified (i.e. just running 'grunt').
    grunt.registerTask('default', 'dev');

    grunt.registerTask('test:unit', ['karma:unit']);
    grunt.registerTask('test:midway', ['karma:midway']);
    grunt.registerTask('test:e2e', ['protractor:all']);
    grunt.registerTask('test:all', ['test:unit', 'test:midway', 'test:e2e']);

    // Build for prod
    grunt.registerTask('prod', [
        'clean',
        'copy:prod',
        'copy:olSource',
        'less',
        'includeSource',  // call before useminPrepare
        'useminPrepare',
        'concat:generated',
        'cssmin:generated',
        'uglify:generated',
        'usebanner', // needs to be before filerev
        'filerev',
        'usemin',
        'htmlmin'    // needs to be after usemin
    ]);

    grunt.registerTask('init', [
        'exec:buildOL',
        'dev'
    ]);

    grunt.registerTask('buildOL', [
        'exec:buildOL',
        'copy:olSource'
    ]);
};
