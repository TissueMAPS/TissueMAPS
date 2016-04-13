// var $injector;

// describe('In restoreAppstateService', function() {
//     // Some fake data
//     var appstateJSON = '{"id":"V7Nl4Noz","name":"asdf","owner":"testuser","isSnapshot":false,"blueprint":{"activeViewerNumber":0,"viewers":[{"experiment":{"channels":[{"imageSize":[30310,23028],"name":"Cell_Mask","pyramidPath":"/experiments/D5YAKwe7/layers/Cell_Mask/"},{"imageSize":[30307,23020],"name":"Channel_01","pyramidPath":"/experiments/D5YAKwe7/layers/Channel_01/"},{"imageSize":[30307,23020],"name":"Channel_02","pyramidPath":"/experiments/D5YAKwe7/layers/Channel_02/"},{"imageSize":[30307,23020],"name":"Channel_03","pyramidPath":"/experiments/D5YAKwe7/layers/Channel_03/"},{"imageSize":[30310,23028],"name":"Nuclei_Mask","pyramidPath":"/experiments/D5YAKwe7/layers/Nuclei_Mask/"},{"imageSize":[30310,23028],"name":"outlines","pyramidPath":"/experiments/D5YAKwe7/layers/outlines/"}],"description":"Very nice exp","id":"D5YAKwe7","name":"150316-30min-PBS"},"viewport":{"channelLayerOptions":[{"additiveBlend":true,"brightness":0,"color":{"a":1,"b":255,"g":255,"r":255},"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30310,23028],"max":0.26666666666666666,"min":0,"name":"Cell_Mask","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Cell_Mask/","visible":false},{"additiveBlend":true,"brightness":0,"color":{"a":1,"b":0,"g":0,"r":255},"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30307,23020],"max":0.16862745098039217,"min":0,"name":"Channel_01","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Channel_01/","visible":true},{"additiveBlend":true,"brightness":0,"color":{"a":1,"b":255,"g":255,"r":255},"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30307,23020],"max":1,"min":0,"name":"Channel_02","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Channel_02/","visible":false},{"additiveBlend":true,"brightness":0,"color":{"a":1,"b":255,"g":255,"r":255},"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30307,23020],"max":1,"min":0,"name":"Channel_03","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Channel_03/","visible":false},{"additiveBlend":true,"brightness":0,"color":{"a":1,"b":255,"g":255,"r":255},"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30310,23028],"max":1,"min":0,"name":"Nuclei_Mask","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Nuclei_Mask/","visible":false},{"additiveBlend":true,"brightness":0,"color":{"a":1,"b":255,"g":255,"r":255},"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30310,23028],"max":1,"min":0,"name":"outlines","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/outlines/","visible":false}],"mapState":{"center":[17448.9697265625,-16881.01171875],"resolution":7.39990234375,"rotation":0,"zoom":4},"selectionHandler":{"selections":[]}}}]}}';

//     var appstate;
//     // Declare variables that will get assigned an actual instance after each
//     // function that was passed to beforeEach is executed
//     var restoreAppstateService, $httpBackend, application, $q, $rootScope;

//     // Load the appstate module, automatically loads all dependencies of
//     // that module (as long as they are listed in the brackets when
//     // declaring the module!).
//     beforeEach(module('tmaps.core'));

//     beforeEach(inject(function(_restoreAppstateService_, _$httpBackend_,
//                                _application_, _$q_, _$rootScope_,
//                                _$injector_) {
//         // Assign the injected variables to the variables s.t. they can be used
//         // in the specs
//         restoreAppstateService = _restoreAppstateService_;
//         $httpBackend = _$httpBackend_;
//         application = _application_;
//         $q = _$q_;
//         $rootScope = _$rootScope_;
//         $injector = _$injector_;

//         // Reparse each time a text is executed since code may alter the
//         // appstate object in the process.
//         appstate = JSON.parse(appstateJSON);

//     }));

//     describe('the function restoreAppstate', function() {
//         beforeEach(function() {
//             $httpBackend.whenGET('/templates/main/viewport.html')
//             .respond(200, '<div id="viewports"></div>');

//             $httpBackend.whenGET('/api/experiments/D5YAKwe7/features?include=min,max')
//             .respond(200, {});

//             $httpBackend.whenGET('/api/experiments/D5YAKwe7/cells')
//             .respond(200, {});

//             $httpBackend.whenGET('/src/core/tools/tools.json')
//             .respond(200, {});

//             spyOn(CellSelectionHandler.prototype, 'addCellOutlines').and.callThrough();

//             restoreAppstateService.restoreAppstate(appstate);
//             $httpBackend.flush();
//         });

//         it('should restore all the Viewers', function() {
//             expect(application.viewers.length == 1);
//             application.viewers.forEach(function(inst) {
//                 expect(inst.constructor.name).toEqual('Viewer');
//             });
//         });

//         it('should add the cell outline layers', function() {
//             application.viewers.forEach(function(inst) {
//                 expect(inst.viewport.selectionHandler.addCellOutlines).toHaveBeenCalled();
//             });
//         });

//         it('should correctly set the experiment of the Viewers', function() {
//             var serializedInstances = appstate.blueprint.viewers;
//             for (var i = 0; i < serializedInstances.length; i++) {
//                 var serializedInst = serializedInstances[i];
//                 var inst = application.viewers[i];
//                 var exp = inst.experiment;
//                 var serializedExp = serializedInst.experiment;

//                 expect(exp.constructor.name).toEqual('Experiment');
//                 expect(exp.name).toEqual(serializedExp.name);
//                 expect(exp.description).toEqual(serializedExp.description);
//                 expect(exp.channels).toEqual(serializedExp.channels);
//             }
//         });

//         describe('when initializing the viewport', function() {
//             var vp;

//             beforeEach(function() {
//                 vp = application.viewers[0].viewport;
//             });

//             it('should add all layers', function() {
//                 // Check that the right amount of layers were added.
//                 expect(vp.channelLayers.length).toEqual(6);
//             });

//             it('should restore the layers\' properties', function(done) {
//                 // Check that colors were restored correctly.
//                 vp.map.then(function(map) {
//                     var red = Color.RED;
//                     var white = Color.WHITE;
//                     expect(vp.channelLayers[1].color.equals(red)).toEqual(true);
//                     expect(vp.channelLayers[1].max).toEqual(0.16862745098039217);
//                     expect(vp.channelLayers[1].visible).toEqual(true);

//                     expect(vp.channelLayers[2].color.equals(white)).toEqual(true);
//                     expect(vp.channelLayers[2].max).toEqual(1);
//                     expect(vp.channelLayers[2].visible).toEqual(false);
//                     done();
//                 });
//                 // Propagate promise resolution to 'then' functions using $apply().
//                 // Without this the deferreds won't be resolved and the above
//                 // then callback will not be called!
//                 $rootScope.$apply();
//             });
//         });
//     });

// });
