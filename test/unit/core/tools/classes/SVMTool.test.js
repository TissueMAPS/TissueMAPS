// describe('In SVMTool', function() {
//     // Load the module of ObjectLayer and its dependencies
//     beforeEach(module('tmaps.core'));

//     // Injected services and factories
//     var $rootScope, $httpBackend;
//     var $q;

//     // Call inject function to get ahold of services, assign to declared
//     // variables. Angular will strip underscores from function arguments to
//     // resolve actual service.
//     beforeEach(inject(function(_$rootScope_, _$httpBackend_, _$q_) {
//         // Assign to variables
//         $rootScope = _$rootScope_;
//         $httpBackend = _$httpBackend_;
//         $q = _$q_;
//     }));


//     var svm;
//     var appstate;
//     var experiment;
//     var viewer;
//     var classificationResult;

//     // Assign sample data each time a test is executed.
//     beforeEach(function() {
//         appstate = {};
//         experiment = {};
//         viewer = {
//             viewport: {
//                 addObjectLayer: jasmine.createSpy('addObjectLayer')
//             },
//             experiment: {
//                 cellMap: $q.when({
//                     1: {},
//                     2: {},
//                     3: {},
//                     4: {}
//                 })
//             }
//         };
//         classificationResult = {
//             classes: [
//                 {
//                     label: 'class1',
//                     color: {r: 255, g: 0, b: 0},
//                     cell_ids: ['1', '2']
//                 },
//                 {
//                     label: 'class2',
//                     color: {r: 0, g: 255, b: 0},
//                     cell_ids: ['3', '4']
//                 }
//             ]
//         };

//         svm = new SVMTool(viewer);
//     });

//     describe('the function handleResult', function() {
//         it('should exist', function() {
//             expect(svm.handleResult).toBeDefined();
//         });

//         it('should for each class add an object layer to the viewport', function() {
//             svm.handleResult(classificationResult);
//             $rootScope.$apply();

//             expect(classificationResult.classes).toBeDefined();


//             // for (var i = 0; i < classificationResult.classes.length; i++) {
//             //     var cls = classificationResult.classes[i];
//             //     var color = Color.fromObject(cls.color);
//             // }
//             expect(viewer.viewport.addObjectLayer).toHaveBeenCalledWith(
//                 jasmine.objectContaining({
//                     name: 'SVM'
//                 })
//             );
//         });
//     });

// });
