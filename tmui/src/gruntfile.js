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
 *      will watch files for change and automatically compile them
 *      (specyfing 'dev' is optional).
 *      This command will also start a development server.
 *      The browser is reloaded automatically as soon as any of the files change.
 *
 *      $ grunt dist
 *
 *      will create a release build in the directory specified by the productionDir variable.
 *
 *      $ grunt test
 *
 *      will start a continous testing cycle.
 *
 *  New tasks should be installed with:
 *
 *      $ cd /path/to/TissueMAPS/client
 *      $ npm install grunt-sometask --save-dev
 */

var path = require('path');

module.exports = function(grunt) {
    'use strict';

    // Execute 'grunt.loadNpmTasks' for all tasks in package.json
    require('load-grunt-tasks')(grunt);
    // Needs to be loaded separately to log execution times
    require('time-grunt')(grunt);
    grunt.loadNpmTasks('grunt-typescript');

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
        rootDir: path.resolve('.'),

        // Styles
        lessDir: 'app/assets/less',   // need to be compiled
        cssDir: 'app/assets/css',    // does not need to be compiled

        // Temp dir where tasks should put intermediate files
        tmpDir: '_tmp',

        // Where to place all files when the app is built for production
        productionDir: '_dist',

        // Where to place the compiled files
        buildDir: '_build',

        olDir: 'app/assets/libs/ol3',

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
            dist: ['<%= productionDir %>'],
            build: ['<%= buildDir %>'],
            tmp: ['<%= tmpDir %>']
        },

        /**
         * Copy the html and image files into the build directory
         */
        copy: {
            dist: {
                files: [
                    {cwd: 'app', expand: true, src: ['src/**/*.html'], dest: '<%= productionDir %>/'},
                    {cwd: 'app', expand: true, src: ['src/**/*.json'], dest: '<%= productionDir %>/'},
                    {cwd: 'app', expand: true, src: ['templates/**/*.html'], dest: '<%= productionDir %>/'},
                    {dest: '<%= productionDir %>/index.html', src: 'app/index.html'},
                    {dest: '<%= productionDir %>/src/toolwindow/index.html', src: 'app/src/toolwindow/index.html'},
                    {cwd: 'app', expand: true, src: ['resources/**'], dest: '<%= productionDir %>/'}
                ]
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
                        '<%= productionDir %>/script-main.min.js',
                        '<%= productionDir %>/src/toolwindow/script-tools.min.js',
                        '<%= productionDir %>/src/toolwindow/style-tools.min.css',
                        '<%= productionDir %>/style-main.min.css'
                    ]
                }
            }
        },

        /*
         * Expand all glob patterns in script and style tags.
         */
        includeSource: {
            options: {
                basePath: 'app',
                templates: {
                    html: {
                        js: '<script src="/{filePath}"></script>'
                    }
                }
            },
            main: {
                files: {
                    'app/index.html': 'app/index.pre.html'
                }
            },
            tools: {
                files: {
                    'app/src/toolwindow/index.html': 'app/src/toolwindow/index.pre.html'
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
            main: [
                'app/index.html',
            ],
            tools: [
                'app/src/toolwindow/index.html'
            ],
            options: {
                dest: '<%= productionDir %>'
            }
        },
        usemin: {
            main: [
                '<%= productionDir %>/index.html',
            ],
            tools: [
                '<%= productionDir %>/src/toolwindow/index.html'
            ],
            options: {
                assetDirs: [
                    '<% productionDir %>',
                    '<% productionDir %>/resources',
                    '<% productionDir %>/resources/img'
                ]
            }
        },
        uglify: {
            options: {
                sourceMap: true,
                compress: false,
                mangle: false,
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
                    // '<%= productionDir %>/resources/img/**/*.{jpg,png,gif,ico}',
                    '<%= productionDir %>/**/*.{js,css}'
                ]
            },
        },

        /*
         * Watch files for changes and execute other tasks.
         */
        watch: {
            // Preprocess html files as soon as one changes
            htmlPre: {
                files: ['app/templates/tools/index.pre.html', 'app/index.pre.html'],
                tasks: ['includeSource']
            },

            // Auto-reload browser when a html changes
            html: {
                options: { livereload: 35760},
                files: [
                    'app/index.html',
                    'app/templates/**/*.html',
                    '!app/templates/tools/index.pre.html' // needs to be globbed first
                ]
            },

            // Automatically compile less files on change
            less: {
                files: ['<%= lessDir %>/**/*.less'],
                tasks: ['less', 'includeSource']
            },

            js: {
                files: ['app/src/**/*.js'],
                tasks: [
                    'includeSource'
                    // , 'test:unit'
                ]
            },

            // ts: {
            //     files: ['app/src/**/*.ts'],
            //     tasks: ['typescript']
            // },


            // jsTest: {
            //     files: ['test/**/*.js'],
            //     tasks: ['karma:unit:run', 'karma:midway:run']
            // },

            // NOTE: Enabling this produces some error messages when running 'watch'
            openlayersSource: {
                files: ['<%= olDir %>/src/ol/**/*.js'],
                tasks: [
                    'exec:buildOLDebug'
                ]
            },

            // Reload grunt (no tasks need to be specified, this is all that's needed)
            grunt: { files: ['gruntfile.js'] }
        },

        connect: {
            dev: {
                options: {
                    port: 8002,
                    base: 'app', // from where to serve files
                    livereload: 35761, // port
                    // open: 'http://localhost:8000/index.html',
                    middleware: function(connect, options) {
                        if (!Array.isArray(options.base)) {
                            options.base = [options.base];
                        }
                        // Setup the proxy
                        var middlewares = [require('grunt-connect-proxy/lib/utils').proxyRequest];
                        // Serve static files.
                        options.base.forEach(function(base) {
                            middlewares.push(connect.static(base));
                        });
                        // Make directory browse-able.
                        var directory = options.directory || options.base[options.base.length - 1];
                        middlewares.push(connect.directory(directory));
                        return middlewares;
                    }
                },
                proxies: [
                    {
                        context: '/api',
                        host: 'localhost',
                        port: 5002,
                        https: false,
                        xforward: false,
                        ws: true // proxy websockets
                    },
                    {
                        context: '/auth',
                        host: 'localhost',
                        port: 5002,
                        https: false,
                        xforward: false,
                        ws: true // proxy websockets
                    }
                ]
            },
            dist: {
                options: {
                    port: 8002,
                    keepalive: true,
                    base: '_dist', // from where to serve files
                    middleware: function(connect, options) {
                        if (!Array.isArray(options.base)) {
                            options.base = [options.base];
                        }
                        // Setup the proxy
                        var middlewares = [require('grunt-connect-proxy/lib/utils').proxyRequest];
                        // Serve static files.
                        options.base.forEach(function(base) {
                            middlewares.push(connect.static(base));
                        });
                        // Make directory browse-able.
                        var directory = options.directory || options.base[options.base.length - 1];
                        middlewares.push(connect.directory(directory));
                        return middlewares;
                    }
                },
                proxies: [
                    {
                        context: '/api',
                        host: 'localhost',
                        port: 5002,
                        https: false,
                        xforward: false,
                        ws: true // proxy websockets
                    },
                    {
                        context: '/auth',
                        host: 'localhost',
                        port: 5002,
                        https: false,
                        xforward: false,
                        ws: true // proxy websockets
                    }
                ]
            }
        },

        /*
         * Execute the python build script for openlayers.
         * This will create the file libs/ol.js.
         */
        exec: {
            buildOLDebug: '(node <%= olDir %>/tasks/build.js <%= olDir %>/config/ol-debug.json app/assets/libs/ol-debug.js)',
            buildOL: '(node <%= olDir %>/tasks/build.js <%= olDir %>/config/ol.json app/assets/libs/ol.js)',
            initOL: '(cd <%= olDir %> && make install)',
            buildTypeScript: 'node_modules/typescript/bin/tsc'
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
                paths: ['<%= lessDir %>'],
                cleancss: false
            },
            compile: {
                files: {
                    // The style.less file imports all other less files
                    '<%= cssDir %>/style-main.css': '<%= lessDir %>/main/style.less',
                    '<%= cssDir %>/style-tools.css': '<%= lessDir %>/tools/style.less'
                }
            }
        },

        typescript: {
            base: {
                src: ['app/src/**/*.ts'],
                // Supplying a single file will result in
                // all ts files be concatenated first. Interfaces can
                // therefore be declared in global scope.
                dest: 'app/build/compiled-ts.js',
                options: {
                    module: 'commonjs', //or commonjs
                    target: 'es5', //or es3
                    // keepDirectoryHierarchy: true,
                    sourceMap: true,
                    declaration: true,
                    references: [
                        'app/typedefs/DefinitelyTyped/underscore/underscore.d.ts',
                        'app/typedefs/DefinitelyTyped/angularjs/angular.d.ts',
                        'app/typedefs/DefinitelyTyped/jquery/jquery.d.ts',
                        'app/typedefs/DefinitelyTyped/openlayers/openlayers.d.ts'
                    ]
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
                    collapseWhitespace: true
                },
                files: {
                    '<%= productionDir %>/index.html': '<%= productionDir %>/index.html',
                    '<%= productionDir %>/src/toolwindow/index.html': '<%= productionDir %>/src/toolwindow/index.html'
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
                logLevel: 'INFO',
                browsers: [
                    'PhantomJS'
                    // 'Chrome'
                ],
                singleRun: true,
                files: [
                    // Files to include everywhere
                    'node_modules/ng-midway-tester/src/ngMidwayTester.js',
                    // Library code
                    'app/assets/libs/bower_components/jquery/dist/jquery.js',
                    'app/assets/libs/unmanaged/jquery-ui.min.js',
                    'app/assets/libs/bower_components/underscore/underscore.js',

                    // 'app/assets/libs/ol3/build/ol.js',
                    'app/assets/libs/ol-debug.js',

                    'app/assets/libs/bower_components/angular/angular.js',
                    'app/assets/libs/bower_components/angular-mocks/angular-mocks.js',
                    'app/assets/libs/bower_components/angular-ui-router/release/angular-ui-router.js',
                    'app/assets/libs/bower_components/angular-sanitize/angular-sanitize.js',
                    'app/assets/libs/bower_components/highcharts/highcharts.js',
                    'app/assets/libs/bower_components/highcharts-ng/dist/highcharts-ng.min.js',
                    'app/assets/libs/bower_components/angular-ui-sortable/sortable.min.js',
                    'app/assets/libs/bower_components/angular-ui-slider/src/slider.js',
                    'app/assets/libs/bower_components/angular-ui-bootstrap-bower/ui-bootstrap-tpls.js',
                    'app/assets/libs/unmanaged/ng-color-picker/color-picker.js',
                    'app/assets/libs/bower_components/perfect-scrollbar/js/perfect-scrollbar.jquery.js',
                    'app/assets/libs/unmanaged/angular-perfect-scrollbar.js',
                    'app/assets/libs/bower_components/momentjs/moment.js',

                    'app/assets/libs/bower_components/ng-websocket/ng-websocket.js',

                    'app/assets/libs/bower_components/tmauth/dist/tmauth.js',

                    // Module declarations
                    'app/src/tmaps.js',
                    'app/src/tmaps.routes.js',
                    'app/src/tmaps.toolwindow.js',

                    // Source
                    'app/build/compiled-ts.js',
                    'app/src/ui/**/*.js',
                    'app/src/toolwindow/**/*.js'
                ]
            },
            unit: {
                singleRun: false,
                captureConsole: true,
                reporters: 'mocha',
                logLevel: 'INFO',
                files: [
                    { src: ['test/unit/**/*.js'] }
                ]
            },
            midway: {
                files: [
                    { src: 'app/assets/libs/bower_components/ngMidwayTester/src/ngMidwayTester.js' },
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
                    { src: 'app/assets/libs/bower_components/ngMidwayTester/src/ngMidwayTester.js' },
                    { src: ['test/midway/**/*.js'] },
                    { src: ['test/e2e/**/*.js'] }
                ]
            },
            cov: {
                singleRun: true,
                preprocessors: {
                    'app/src/**/*.js': 'coverage'
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
    // This will also start a development server that serves files
    // without needing to minify them first (much faster).
    grunt.registerTask('dev', [
        'clean:build',
        'clean:tmp',
        'less',
        'exec:buildTypeScript',
        'includeSource',
        'configureProxies:dev',
        'connect:dev',
        'watch'
    ]);
    // The dev task is also executed when no task is specified (i.e. just running 'grunt').
    grunt.registerTask('default', 'dev');

    grunt.registerTask('test:unit', ['karma:unit']);
    grunt.registerTask('test', ['karma:unit']);
    grunt.registerTask('test:midway', ['karma:midway']);
    grunt.registerTask('test:e2e', ['protractor:all']);
    grunt.registerTask('test:all', ['test:unit', 'test:midway', 'test:e2e']);

    // Build for production
    grunt.registerTask('dist', [
        'clean',
        'copy:dist',
        'less',
        'exec:buildTypeScript',
        'includeSource',  // call before useminPrepare

        // // Main part
        // 'useminPrepare:main',
        // 'concat:generated',
        // 'cssmin:generated',        
        // 'uglify', 
        // 'usebanner', // needs to be before filerev
        // // 'filerev',
        // 'usemin:main',

        // Tools part
        'useminPrepare:tools',
        'concat:generated',
        'cssmin:generated',        
        'uglify', 
        'usebanner', // needs to be before filerev
        // 'filerev',
        'usemin:tools',

        'htmlmin'    // needs to be after usemin
    ]);

    // A task to test the built project using a test server
    grunt.registerTask('dist-server', [
        'configureProxies:dist',
        'connect:dist'
    ]);

    grunt.registerTask('init', [
        'exec:initOL',
        'exec:buildOL',
        'dev'
    ]);

    grunt.registerTask('buildOLDebug', [
        'exec:buildOLDebug',
        'dev'
    ]);

    grunt.registerTask('buildOL', [
        'exec:buildOL'
    ]);
};
