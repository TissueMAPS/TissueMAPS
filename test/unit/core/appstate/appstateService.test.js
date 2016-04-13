// describe('In appstateService', function() {

//     var appstateHash = 'ddfg438';
//     var serializedApp = {
//         activeInstanceNumber: 0,
//         viewers: [{}]
//     };
//     var appstateServerResponse = {
//         id: appstateHash,
//         name: 'fakeAppState',
//         is_snapshot: false,
//         owner: 'testuser',
//         blueprint: serializedApp
//     };
//     var getStatesResponse = {
//         owned: [appstateServerResponse],
//         shared: [appstateServerResponse]
//     };
//     var appstate = {
//         id: appstateHash,
//         name: 'fakeAppState',
//         isSnapshot: false,
//         owner: 'testuser',
//         blueprint: serializedApp
//     };
//     var appstateSnapshot = {
//         id: appstateHash,
//         name: 'fakeAppState',
//         isSnapshot: true,
//         owner: 'testuser',
//         blueprint: serializedApp
//     };

//     // Declare variables that will get assigned an actual instance after each
//     // function that was passed to beforeEach is executed
//     var appstateService, $httpBackend, application, $q,
//         $location, $modal, restoreAppstateService, $rootScope;

//     // Load the appstate module, automatically loads all dependencies of
//     // that module (as long as they are listed in the brackets when
//     // declaring the module!).
//     beforeEach(module('tmaps.core'));

//     beforeEach(inject(function(_appstateService_, _$httpBackend_, _application_, _$q_, _$location_, _$modal_, _restoreAppstateService_, _$rootScope_) {
//         // Assign the injected variables to the variables s.t. they can be used
//         // in the specs
//         appstateService = _appstateService_;
//         $httpBackend = _$httpBackend_;
//         application = _application_;
//         $q = _$q_;
//         $location = _$location_;
//         $modal = _$modal_;
//         restoreAppstateService = _restoreAppstateService_;
//         $rootScope = _$rootScope_;

//         // Create proxy functions on appstateService that can be tracked
//         spyOn(appstateService, 'promptForSaveAs');
//         // callThrough: the dummy/spy function should actually call the
//         // implementation
//         spyOn(appstateService, 'getLinkForSnapshot').and.callThrough();
//         spyOn(appstateService, 'setCurrentState').and.callThrough();
//         spyOn(appstateService, 'loadState').and.callThrough();
//         spyOn(appstateService, 'loadStateFromId').and.callThrough();
//         spyOn(appstateService, 'shareState').and.callThrough();
//         spyOn(restoreAppstateService, 'restoreAppstate');
//         spyOn($modal, 'open').and.callThrough();
//     }));


//     describe('the function hasCurrentState', function() {

//         it('should return true if the state has been saved', function() {
//             appstateService.setCurrentState(appstate);

//             expect(appstateService.hasCurrentState()).toBe(true);
//         });

//         it('should return false if the state has not been saved', function() {
//             expect(appstateService.hasCurrentState()).toBe(false);
//         });

//     });

//     describe('the function getStates', function() {

//         it('should return a promise of the clientized version of the server response', function(done) {
//             $httpBackend.expectGET('/api/appstates')
//             .respond(200, getStatesResponse);

//             var states = appstateService.getStates();
//             $httpBackend.flush();

//             states.then(function(resp) {
//                 expect(resp.owned[0].isSnapshot).toBeDefined();
//                 expect(resp.shared[0].isSnapshot).toBeDefined();
//                 done();
//             });

//             $rootScope.$apply();
//         });

//         it('should raise en error if retrieval didn\'t work', function() {
//             // TODO
//         });

//     });

//     describe('the function loadState', function() {

//         beforeEach(function() {
//             appstateService.loadState(appstate);
//         });

//         it('should set the current state ', function() {
//             expect(appstateService.setCurrentState).toHaveBeenCalledWith(appstate);
//         });

//         it('should load the state', function() {
//             expect(restoreAppstateService.restoreAppstate).toHaveBeenCalledWith(appstate);
//         });

//         it('should update the url bar', function() {
//             expect($location.search().state).toEqual(appstateHash);
//         });

//     });

//     describe('the function loadStateFromId', function() {
//         var handler;
//         beforeEach(function() {
//             handler = $httpBackend.expectGET('/api/appstates/' + appstateHash)
//             .respond(200, appstateServerResponse);
//         });

//         it('should load the requested state', function() {
//             appstateService.loadStateFromId(appstateHash);
//             $httpBackend.flush();

//             expect(appstateService.loadState).toHaveBeenCalled();
//         });

//         it('should raise en error if the appstate was not found', function() {
//             handler.respond(404);

//             var call = function() {
//                 appstateService.loadStateFromId(appstateHash);
//                 $httpBackend.flush();
//             };

//             expect(call).toThrowError(/error/);
//         });

//         it('should update the url bar', function() {
//             appstateService.loadStateFromId(appstateHash);
//             $httpBackend.flush();

//             expect($location.search().state).toEqual(appstateHash);
//         });

//     });


//     describe('the function saveStateAs', function() {

//         var handler;

//         beforeEach(function() {
//             handler = $httpBackend.expectPOST('/api/appstates').respond(200,
//                 appstateServerResponse
//             );
//         });

//         it('should save the state', function() {
//             appstateService.saveStateAs('some name', 'some description');
//             $httpBackend.flush();

//             expect(appstateService.currentState.id).toEqual(appstateServerResponse.id);
//         });

//         it('should update the current location', function() {
//             appstateService.saveStateAs('some name', 'some description');
//             $httpBackend.flush();

//             expect($location.search().state).toEqual(appstateServerResponse.id);
//         });

//         it('should set the current state', function() {
//             appstateService.saveStateAs('some name', 'some description');
//             $httpBackend.flush();

//             expect(appstateService.currentState.id).toEqual(appstateServerResponse.id);
//         });

//         it('should set the last saved at date ', function() {
//             appstateService.saveStateAs('some name', 'some description');
//             $httpBackend.flush();

//             expect(appstateService.currentState).toBeDefined();
//         });

//         it('should throw an error if the user tries to resave a snapshot', function() {
//             appstateService.loadState(appstateSnapshot);

//             var call = function() {
//                 appstateService.saveStateAs('some name', 'some description');
//                 $httpBackend.flush();
//             };

//             expect(call).toThrowError(/A snapshot can't be saved/);
//         });
//     });

//     describe('the function saveState', function() {

//         var handler;

//         beforeEach(function() {
//             handler = $httpBackend.expectPUT('/api/appstates/' + appstate.id)
//             .respond(200, appstateServerResponse);
//         });

//         it('should save the state', function() {
//             appstateService.loadState(appstate);
//             appstateService.saveState();
//             $httpBackend.flush();

//             expect(appstateService.currentState.id).toEqual(appstateServerResponse.id);
//         });

//         it('should throw en error if the user tries to resave a snapshot', function() {
//             var call = function() {
//                 appstateService.loadState(appstateSnapshot);
//                 appstateService.saveState();
//                 $httpBackend.flush();
//             };

//             expect(call).toThrowError(/Can't save snapshots!/);
//         });
//     });


//     describe('the function shareState', function() {

//         beforeEach(function() {
//             $httpBackend.whenGET(
//                 '/api/appstates/' + appstateHash + '/snapshots'
//             ).respond(200, appstateSnapshot)

//             $httpBackend.expectGET(
//                 '/templates/main/appstate/share-appstate-dialog.html'
//             ).respond(200, ''); // respond with empty template
//         });

//         it('should throw an error if the user tries to reshare a snapshot', function() {
//             var call = function() {
//                 appstateService.loadState(appstateSnapshot);
//                 appstateService.shareState();
//             };
//             expect(call).toThrowError(/snapshot/);
//         });

//         it('should throw an error if the user tries to share a nonexisting appstate', function() {
//             var call = function() {
//                 appstateService.shareState();
//             };
//             expect(call).toThrowError(/Appstate needs to be saved/);
//         });

//         it('should make a GET request to the server', function() {
//             $httpBackend.expectGET('/api/appstates/' + appstateHash).respond(200, appstate);
//             appstateService.loadState(appstate);

//             appstateService.shareState();
//         });

//         it('should open a modal', function() {
//             appstateService.loadState(appstate);
//             appstateService.shareState();
//             $httpBackend.flush();

//             expect($modal.open).toHaveBeenCalled();
//         });

//         it('should generate the snapshot URL', function() {
//             appstateService.loadState(appstate);
//             appstateService.shareState();
//             $httpBackend.flush();

//             expect(appstateService.getLinkForSnapshot).toHaveBeenCalled();
//         });
//     });


//     describe('the function getLinkForSnapshot', function() {
//         it('should generate a snapshot URL given a snapshot', function() {
//             var link = appstateService.getLinkForSnapshot(appstateSnapshot);
//             expect(link).toEqual('http://server:80/#/viewport?snapshot=' + appstateSnapshot.id);
//         });

//     });
// });
