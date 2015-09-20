var appstateHash = 'ddfg438';
var serializedApp = {
    activeInstanceNumber: 0,
    appInstances: [{}]
};
var appstateServerResponse = {
    id: appstateHash,
    name: 'fakeAppState',
    is_snapshot: false,
    owner: 'testuser',
    blueprint: serializedApp
};
var getStatesResponse = {
    owned: [appstateServerResponse],
    shared: [appstateServerResponse]
};
var appstate = {
    id: appstateHash,
    name: 'fakeAppState',
    isSnapshot: false,
    owner: 'testuser',
    blueprint: serializedApp
};


describe('appstateService:', function() {

    // Declare variables that will get assigned an actual instance after each
    // function that was passed to beforeEach is executed
    var appstateService, $httpBackend, application, $q, dialogService,
        $location, $modal, applicationDeserializer, $rootScope;

    // Load the application service mock before
    beforeEach(module('tmaps.mock.core'));

    // Load the appstate module, automatically loads all dependencies of
    // that module (as long as they are listed in the brackets when
    // declaring the module!).
    beforeEach(module('tmaps.main.appstate'));

    beforeEach(inject(function(_appstateService_, _$httpBackend_, _application_, _$q_, _dialogService_, _$location_, _$modal_, _applicationDeserializer_, _$rootScope_) {
        // Assign the injected variables to the variables s.t. they can be used
        // in the specs
        appstateService = _appstateService_;
        $httpBackend = _$httpBackend_;
        application = _application_;
        $q = _$q_;
        dialogService = _dialogService_;
        $location = _$location_;
        $modal = _$modal_;
        applicationDeserializer = _applicationDeserializer_;
        $rootScope = _$rootScope_;

        // Create proxy functions on appstateService that can be tracked
        spyOn(appstateService, 'promptForSaveAs');
        // callThrough: the dummy/spy function should actually call the
        // implementation
        spyOn(appstateService, 'setCurrentState').and.callThrough();
        spyOn(appstateService, 'loadState').and.callThrough();
        spyOn(appstateService, 'loadStateFromId').and.callThrough();
        spyOn(appstateService, 'shareState').and.callThrough();
        spyOn(applicationDeserializer, 'deserialize');
        spyOn($modal, 'open').and.callThrough();
    }));


    describe('hasCurrentState', function() {

        it('should return true if the state has been saved', function() {
            appstateService.currentState = appstate;

            expect(appstateService.hasCurrentState()).toBe(true);
        });

        it('should return false if the state has not been saved', function() {
            expect(appstateService.hasCurrentState()).toBe(false);
        });

    });

    describe('getStates', function() {

        it('should return a promise of the clientized version of the server response', function(done) {
            $httpBackend.expectGET('/api/appstates')
            .respond(200, getStatesResponse);

            var states = appstateService.getStates();
            $httpBackend.flush();

            states.then(function(resp) {
                expect(resp.owned[0].isSnapshot).toBeDefined();
                expect(resp.shared[0].isSnapshot).toBeDefined();
                done();
            });

            $rootScope.$apply();
        });

        it('should raise en error if retrieval didn\'t work', function() {
            // TODO
        });

    });

    describe('loadState', function() {

        it('should set the current state ', function() {
            appstateService.loadState(appstate);

            expect(appstateService.setCurrentState).toHaveBeenCalledWith(appstate);
        });

        it('should load the state', function() {
            appstateService.loadState(appstate);

            expect(applicationDeserializer.deserialize).toHaveBeenCalledWith(appstate.blueprint);
        });

        it('should update the url bar', function() {
            appstateService.loadStateFromId(appstateHash);
            $httpBackend.flush();

            expect($location.search().state).toEqual(appstateHash);
        });

    });

    describe('loadStateFromId', function() {
        var handler;
        beforeEach(function() {
            handler = $httpBackend.expectGET('/api/appstates/' + appstateHash)
            .respond(200, appstateServerResponse);
        });

        it('should load the requested state', function() {
            appstateService.loadState(appstate);

            appstateService.loadStateFromId(appstateHash);
            $httpBackend.flush();

            expect(appstateService.loadState).toHaveBeenCalled();
        });

        it('should raise en error if the appstate was not found', function() {
            handler.respond(404);

            var call = function() {
                appstateService.loadStateFromId(appstateHash);
                $httpBackend.flush();
            };

            expect(call).toThrowError(/error/);
        });

    });


    describe('saveStateAs', function() {

        var handler;

        beforeEach(function() {
            handler = $httpBackend.expectPOST('/api/appstates').respond(200,
                appstateServerResponse
            );
        });

        it('should save the state', function() {
            appstateService.saveStateAs('some name', 'some description');
            $httpBackend.flush();

            expect(appstateService.currentState.id).toEqual(appstateServerResponse.id);
        });

        it('should update the current location', function() {
            appstateService.saveStateAs('some name', 'some description');

            $rootScope.$apply();

            expect($location.search().state).toEqual(appstateServerResponse.id);
        });

        it('set the current state', function() {
            appstateService.saveStateAs('some name', 'some description');
            $httpBackend.flush();

            expect(appstateService.setCurrentState).toHaveBeenCalled();
        });

        it('set the last saved at date ', function() {
            appstateService.saveStateAs('some name', 'some description');
            $httpBackend.flush();

            expect(appstateService.currentState).toBeDefined();
        });
    });

//     describe('loading appstates from ids:', function() {
//         var requestHandler;
//         var resp = makeFakeResponse(false); // create fake appstate

//         beforeEach(function() {
//             requestHandler = $httpBackend.expectGET('/api/appstates/' + fakeHash)
//                                          .respond(200, resp);
//         });

//         it('states are loaded if response is positive', function() {
//             appstateService.loadStateFromId(fakeHash);
//             $httpBackend.flush();

//             expect(appstateService.loadState).toHaveBeenCalled();
//         });

//         it('when a state is loaded, the url bar is updated', function() {
//             appstateService.loadStateFromId(fakeHash);
//             $httpBackend.flush();

//             expect($location.search().state).toEqual(fakeHash);
//         });

//         it('error is thrown if response is negative', function() {
//             requestHandler.respond(404, 'asdf');

//             expect(function() {
//                 appstateService.loadStateFromId(fakeHash);
//                 $httpBackend.flush();
//             }).toThrow();
//         });
//     });




//     describe('loading snapshots from ids:', function() {
//         var requestHandler;
//         var resp = makeFakeResponse(true); // create fake snapshot

//         beforeEach(function() {
//             requestHandler = $httpBackend.expectGET('/snapshots/' + fakeHash)
//                                          .respond(200, resp);
//         });

//         it('snapshots are loaded if response is positive', function() {
//             appstateService.loadSnapshotFromId(fakeHash);
//             $httpBackend.flush();

//             expect(appstateService.loadState).toHaveBeenCalled();
//         });

//         it('when a snapshot is loaded the location bar is updated', function() {
//             appstateService.loadSnapshotFromId(fakeHash);
//             $httpBackend.flush();

//             expect($location.search().snapshot).toEqual(fakeHash);
//         });

//         it('error is thrown if response is negative', function() {
//             requestHandler.respond(404, 'asdf');

//             expect(function() {
//                 appstateService.loadSnapshotFromId(fakeHash);
//                 $httpBackend.flush();
//             }).toThrow();
//         });
//     });



//     describe('if the appstate hasn\'t been saved yet', function() {

//         it('"stateHasBeenSavedAlready" should return false',
//            function() {
//             expect(appstateService.stateHasBeenSavedAlready()).toBe(false);
//         });

//         it('calling the save function should trigger a "Save As" dialog', function() {
//             appstateService.saveState();

//             expect(appstateService.promptForSaveAs).toHaveBeenCalled();
//         });

//         it('trying to share the state throws an error', function() {
//             expect(appstateService.shareState).toThrowError(/saved/);
//         });
//     });



//     describe('if the current appstate is a snapshot', function() {
//         // Create a fake snapshot
//         var response = $.extend(true, {}, appstate);
//         response.is_snapshot = true;

//         it('can\'t be saved in any way', function() {
//             $httpBackend.expectGET('/api/appstates/' + appstateHash)
//             .respond(200, response);

//             appstateService.loadStateFromId(appstateHash);
//             $httpBackend.flush(); // perform all requests registered on the backend

//             var clientSideReprOfState = {
//                 id: response.id,
//                 name: response.name,
//                 isSnapshot: response.is_snapshot,
//                 owner: response.owner,
//                 blueprint: response.blueprint
//             };

//             // The snapshot should be loaded
//             expect(appstateService.loadState).toHaveBeenCalledWith(clientSideReprOfState);
//             expect(applicationDeserializer.initFromBlueprint)
//             .toHaveBeenCalledWith(response.blueprint);

//             // But trying to save it again should throw an error
//             // -- if done through 'save'
//             expect(appstateService.saveState).toThrowError(/snapshot/);
//             // -- and if done through 'save as'
//             expect(function() {
//                 appstateService.saveStateAs('some name', 'some desc');
//             }).toThrowError(/snapshot/);
//         });

//     });



    // describe('sharing appstates:', function() {
    //     it('can\'t be done when the state is not saved', function() {
    //         expect(appstateService.shareState).toThrowError(/saved/);
    //     });

    //     it('opens a modal and calls the server', function() {
    //         resp = makeFakeResponse(false); // create fake appstate
    //         $httpBackend.expectGET('/api/appstates/' + fakeHash).respond(200, resp);

    //         appstateService.loadStateFromId(fakeHash);
    //         $httpBackend.flush();

    //         snapshot = makeFakeResponse(true); // create fake snapshot
    //         $httpBackend.expectGET(
    //             '/templates/main/appstate/share-appstate-dialog.html'
    //         ).respond(200, ''); // respond with empty template
    //         $httpBackend.expectPOST(
    //             '/api/appstates/' + fakeHash + '/snapshots'
    //         ).respond(200, snapshot); // respond with fake app state

    //         appstateService.shareState();
    //         $httpBackend.flush();

    //         expect($modal.open).toHaveBeenCalled();
    //     });
    // });

});
