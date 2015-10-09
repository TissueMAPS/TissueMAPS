describe('In SVMTool', function() {
    // Load the module of ObjectLayer and its dependencies
    beforeEach(module('tmaps.core'));

    // Injected services and factories
    var $rootScope, $httpBackend;
    var $q;

    // Call inject function to get ahold of services, assign to declared
    // variables. Angular will strip underscores from function arguments to
    // resolve actual service.
    beforeEach(inject(function(_$rootScope_, _$httpBackend_, _$q_) {
        // Assign to variables
        $rootScope = _$rootScope_;
        $httpBackend = _$httpBackend_;
        $q = _$q_;
    }));


    var svm;
    var appstate;
    var experiment;
    var appInstance;
    var classificationResult;

    // Assign sample data each time a test is executed.
    beforeEach(function() {
        appstate = {};
        experiment = {};
        appInstance = {
            viewport: {
                addObjectLayer: jasmine.createSpy('addObjectLayer')
            },
            experiment: {
                cellMap: $q.when({
                    1: {},
                    2: {},
                    3: {},
                    4: {}
                })
            }
        };
        classificationResult = {
            classes: [
                {
                    label: 'class1',
                    color: new Color(255, 0, 0),
                    cells: ['1', '2']
                },
                {
                    label: 'class2',
                    color: new Color(0, 255, 0),
                    cells: ['3', '4']
                }
            ]
        };

        svm = new SVMTool(appInstance);
    });

    describe('the function handleResult', function() {
        it('should exist', function() {
            expect(svm.handleResult).toBeDefined();
        });

        it('should for each class add an object layer to the viewport', function() {
            svm.handleResult(classificationResult);
            $rootScope.$apply();

            for (var i = 0; i < classificationResult.classes.length; i++) {
                var cls = classificationResult.classes[i];
                var color = Color.createFromObject(cls.color);
                expect(appInstance.viewport.addObjectLayer).toHaveBeenCalledWith(
                    jasmine.objectContaining({
                        strokeColor: color,
                        fillColor: new Color(0, 0, 0, 0),
                        name: cls.label
                    })
                );
            }
        });
    });

});
