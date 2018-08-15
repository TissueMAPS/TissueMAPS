var $injector;

// var $injector = angular.injector(['tmaps.core']);
describe('In Tool', function() {
    // Load the module of ObjectLayer and its dependencies
    beforeEach(module('tmaps.core'));


    // Injected services and factories
    var $window, $rootScope, $httpBackend;
    var $http, $q;

    // Call inject function to get ahold of services, assign to declared
    // variables. Angular will strip underscores from function arguments to
    // resolve actual service.
    beforeEach(inject(function(_$window_, _$rootScope_,
                               _$httpBackend_, _$http_, _$q_, _$injector_) {
        // Assign to variables
        $window = _$window_;
        $rootScope = _$rootScope_;
        $httpBackend = _$httpBackend_;
        $http = _$http_;
        $q = _$q_;
        $injector = _$injector_;

        spyOn($window, 'open').and.callThrough();
    }));


    // Declare sample data that will be used throughout the tests.
    var tool;
    var toolTemplateUrl = '/some/url/to/template';
    var toolTemplate = '<div>test</div>';

    var appstate;
    var experiment;
    var viewer;
    var toolInstance;

    // Assign sample data each time a test is executed.
    beforeEach(function() {
        appstate = {};
        experiment = {};
        viewer = {
            viewport: {
                elementScope: $q.when(jasmine.createSpyObj('elementScope', [
                    '$broadcast'
                ]))
            }
        };
        toolInstance = {
            id: 10
        };

        tool = new FeatureStatsTool(viewer);
    });

    // Setup the server endpoints (without setting up expectations)
    beforeEach(function() {
        $httpBackend.whenPOST('/api/tools/FeatureStats/instances')
        .respond(200, toolInstance);

        $httpBackend.whenGET(toolTemplateUrl)
        .respond(200, toolTemplate);

        // $httpBackend.whenGET('/src/toolwindow/index.html')
        // .respond(200, '<html><body><ui-view></ui-view></body></html>');
    });

    describe('the function getIdSlug', function() {
        function createToolGivenId(id) {
            var t = new Tool(
                {},
                id,
                'some name',
                'some desc',
                'some template url',
                'some icon',
                123,
                123
            );
            return t;
        }

        it('makes the tool\'s id URL-compatible', function() {
            var t = createToolGivenId('SomeId');
            expect(t.getIdSlug()).toEqual('someid');

            var t = createToolGivenId('SomeId99');
            expect(t.getIdSlug()).toEqual('someid99');

            var t = createToolGivenId('Some-Id');
            expect(t.getIdSlug()).toEqual('some-id');

            var t = createToolGivenId('---SOME__ID--');
            expect(t.getIdSlug()).toEqual('some-id');

            var t = createToolGivenId('**(Some)(id__)');
            expect(t.getIdSlug()).toEqual('some-id');

            var t = createToolGivenId('so me-id');
            expect(t.getIdSlug()).toEqual('so-me-id');
        });
    });

    describe('the function createNewWindow', function() {
        // it('should create a tool window on the server', function() {
        //     $httpBackend.expectPOST('/api/tools/SomeTool/instances')
        //     .respond(200, toolInstance);

        //     tool.createNewWindow();
        // });
        it('should add the window to windows', function() {
            var tw = tool.createNewWindow();

            expect(tool.windows.indexOf(tw)).toEqual(0);
        });


        it('should open a new window', function() {
            tool.createNewWindow();

            expect($window.open).toHaveBeenCalledWith(
                '/src/toolwindow/', 'FeatureStats',
                'toolbar=no,menubar=no,titebar=no,location=no,directories=no,replace=no,width=600,height=850'
            );
        });

        it('should set some required tmaps objects on the new windows global scope', function() {
            var toolWindow = tool.createNewWindow();
            var win = toolWindow.windowObject;

            expect(win.init).toBeDefined();
            expect(win.init.viewer).toEqual(viewer);
            expect(win.init.viewportScope).toEqual(viewer.viewport.elementScope);
            expect(win.init.toolWindow).toBeDefined();
            expect(win.init.tool).toEqual(tool);

        });
    });

//     describe('the function removeToolWindow', function() {
//         it('should delete the window server-side');

//         it('should close the window client-side', function() {
//             pending();

//             var newWindow = tool.createNewWindow(appstate, experiment);

//             tool.removeToolWindow(tool.windows[0]);
//             $httpBackend.flush();

//             expect(tool.windows.length).toEqual(0);
//             expect(newWindow.closed).toEqual(true);
//         });
//     });

    describe('an open toolwindow', function() {
        it('should display the tools template', function() {
            pending();
            // $httpBackend.expectGET('/src/toolwindow/index.html')
            // .respond(200, '<html><body><ui-view></ui-view></body></html>');

            // var newWindow = tool.createNewWindow(appstate, experiment);
        });

        it('should cause its removal when it is closed', function() {
            var twin = tool.createNewWindow();
            expect(tool.windows.indexOf(twin)).toEqual(0);
            twin.windowObject.close();
            expect(tool.windows.indexOf(twin)).toEqual(-1);
        });

//         it('should request the tools remote deletion upon closing the window', function() {
//             var newWindow = tool.createNewWindow(appstate, experiment);
//             $httpBackend.flush();

//             $httpBackend.expectDELETE('/api/tool_instances/' + toolInstance.id)
//             .respond(200, {});

//             newWindow.then(function(win) {
//                 win.close();
//             });

//             $rootScope.$apply();
//         });
    });

    describe('the function sendRequest', function() {
        var handler, payload, response;

        beforeEach(function() {
            payload = {
                message: 'hello'
            };
            response = {
                result: {
                    message: 'all is well :)'
                }
            };
            handler = $httpBackend.whenPOST('/api/tools/' + tool.id + '/request', {
                payload: payload
            }).respond(200, response);
        });
        it('should send the payload to the right endpoint', function() {
            pending();
            var payload = {
                message: 'hello'
            };
            $httpBackend.expectPOST('/api/tools/' + tool.id + '/request', {
                payload: payload
            }).respond(200, {});
            tool.sendRequest(payload);
            $httpBackend.flush();
        });

        it('should broadcast messages on the viewport scope when succeeding', function(done) {
            pending();
            tool.sendRequest(payload);
            $httpBackend.flush();
            tool.viewer.viewport.elementScope.then(function(vpScope) {
                expect(vpScope.$broadcast).toHaveBeenCalledWith('toolRequestSent');
                expect(vpScope.$broadcast).toHaveBeenCalledWith('toolRequestDone');
                expect(vpScope.$broadcast).toHaveBeenCalledWith('toolRequestSuccess');
                done();
            });

            $rootScope.$apply();
        });

        it('should broadcast messages on the viewport scope when failing', function(done) {
            pending();
            handler.respond(500, 'some error message');
            var payload = {
                message: 'hello'
            };
            tool.sendRequest(payload);
            $httpBackend.flush();
            tool.viewer.viewport.elementScope.then(function(vpScope) {
                expect(vpScope.$broadcast).toHaveBeenCalledWith('toolRequestSent');
                expect(vpScope.$broadcast).toHaveBeenCalledWith('toolRequestDone');
                expect(vpScope.$broadcast).toHaveBeenCalledWith('toolRequestFailed', 'some error message');
                done();
            });

            $rootScope.$apply();
        });

        it('should add the result to the results array', function() {
            pending();
            expect(tool.results.length).toEqual(0);
            tool.sendRequest(payload);
            $httpBackend.flush();
            expect(tool.results.length).toEqual(1);
        });

    });

});
