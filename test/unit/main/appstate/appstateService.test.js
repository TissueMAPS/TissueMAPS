var fakeHash = 'ddfg438';

function makeFakeResponse(isSnapshot) {
    return {
        id: fakeHash,
        name: 'fakeAppState',
        is_snapshot: isSnapshot,
        owner: 'testuser',
        blueprint: '{}'
    };
}

describe('appstateService:', function() {

    // Declare variables that will get assigned an actual instance after each
    // function that was passed to beforeEach is executed
    var appstateService, $httpBackend, application, $q, dialogService,
        $location, $modal;

    // Load the application service mock before
    beforeEach(module('tmaps.mock.core'));

    // Load the appstate module, automatically loads all dependencies of
    // that module (as long as they are listed in the brackets when
    // declaring the module!).
    beforeEach(module('tmaps.main.appstate'));

    beforeEach(inject(function(_appstateService_, _$httpBackend_, _application_, _$q_, _dialogService_, _$location_, _$modal_) {
        // Assign the injected variables to the variables s.t. they can be used
        // in the specs
        appstateService = _appstateService_;
        $httpBackend = _$httpBackend_;
        application = _application_;
        $q = _$q_;
        dialogService = _dialogService_;
        $location = _$location_;
        $modal = _$modal_;

        // Create trackable dummy functions on the dummy application object
        // application.initFromBlueprint = jasmine.createSpy('initFromBlueprint');
        // application.toBlueprint = jasmine.createSpy('toBlueprint').and.returnValue($q.when({}));

        // Create proxy functions on appstateService that can be tracked
        spyOn(appstateService, 'promptForSaveAs');
        // callThrough: the dummy/spy function should actually call the
        // implementation
        spyOn(appstateService, 'loadState').and.callThrough();
        spyOn(appstateService, 'loadStateFromId').and.callThrough();
        spyOn(appstateService, 'shareState').and.callThrough();
        spyOn($modal, 'open').and.callThrough();
    }));



    describe('the function "saveStateAs"', function() {
        var resp = makeFakeResponse(false);

        beforeEach(function() {
            $httpBackend.expectPOST('/api/appstates').respond(200, resp);
            appstateService.saveStateAs('some name', 'some description');
            $httpBackend.flush(); // perform all requests registered on the backend
        });

        it('should save the state', function() {
            expect(appstateService.currentState.id).toEqual(resp.id);
        });

        it('should update the current location', function() {
            expect($location.search()).toEqual({
                'state': resp.id
            });
        });
    });



    describe('loading appstates from ids:', function() {
        var requestHandler;
        var resp = makeFakeResponse(false); // create fake appstate

        beforeEach(function() {
            requestHandler = $httpBackend.expectGET('/api/appstates/' + fakeHash)
                                         .respond(200, resp);
        });

        it('states are loaded if response is positive', function() {
            appstateService.loadStateFromId(fakeHash);
            $httpBackend.flush();

            expect(appstateService.loadState).toHaveBeenCalled();
        });

        it('when a state is loaded, the url bar is updated', function() {
            appstateService.loadStateFromId(fakeHash);
            $httpBackend.flush();

            expect($location.search().state).toEqual(fakeHash);
        });

        it('error is thrown if response is negative', function() {
            requestHandler.respond(404, 'asdf');

            expect(function() {
                appstateService.loadStateFromId(fakeHash);
                $httpBackend.flush();
            }).toThrow();
        });
    });




    describe('loading snapshots from ids:', function() {
        var requestHandler;
        var resp = makeFakeResponse(true); // create fake snapshot

        beforeEach(function() {
            requestHandler = $httpBackend.expectGET('/snapshots/' + fakeHash)
                                         .respond(200, resp);
        });

        it('snapshots are loaded if response is positive', function() {
            appstateService.loadSnapshotFromId(fakeHash);
            $httpBackend.flush();

            expect(appstateService.loadState).toHaveBeenCalled();
        });

        it('when a snapshot is loaded the location bar is updated', function() {
            appstateService.loadSnapshotFromId(fakeHash);
            $httpBackend.flush();

            expect($location.search().snapshot).toEqual(fakeHash);
        });

        it('error is thrown if response is negative', function() {
            requestHandler.respond(404, 'asdf');

            expect(function() {
                appstateService.loadSnapshotFromId(fakeHash);
                $httpBackend.flush();
            }).toThrow();
        });
    });



    describe('if the appstate hasn\'t been saved yet', function() {

        it('"stateHasBeenSavedAlready" should return false',
           function() {
            expect(appstateService.stateHasBeenSavedAlready()).toBe(false);
        });

        it('calling the save function should trigger a "Save As" dialog', function() {
            appstateService.saveState();

            expect(appstateService.promptForSaveAs).toHaveBeenCalled();
        });

        it('trying to share the state throws an error', function() {
            expect(appstateService.shareState).toThrowError(/saved/);
        });
    });



    describe('if the current appstate is a snapshot', function() {
        // Create a fake snapshot
        resp = makeFakeResponse(true);

        it('can\'t be saved in any way', function() {
            $httpBackend.expectGET('/api/appstates/' + fakeHash).respond(200, resp);

            appstateService.loadStateFromId(fakeHash);
            $httpBackend.flush(); // perform all requests registered on the backend

            var clientSideReprOfState = {
                id: resp.id,
                name: resp.name,
                isSnapshot: resp.is_snapshot,
                owner: resp.owner,
                blueprint: resp.blueprint
            };

            // The snapshot should be loaded
            expect(appstateService.loadState).toHaveBeenCalledWith(clientSideReprOfState);
            expect(application.initFromBlueprint).toHaveBeenCalledWith(resp.blueprint);

            // But trying to save it again should throw an error
            // -- if done through 'save'
            expect(appstateService.saveState).toThrowError(/snapshot/);
            // -- and if done through 'save as'
            expect(function() {
                appstateService.saveStateAs('some name', 'some desc');
            }).toThrowError(/snapshot/);
        });

    });



    describe('sharing appstates:', function() {
        it('can\'t be done when the state is not saved', function() {
            expect(appstateService.shareState).toThrowError(/saved/);
        });

        it('opens a modal and calls the server', function() {
            resp = makeFakeResponse(false); // create fake appstate
            $httpBackend.expectGET('/api/appstates/' + fakeHash).respond(200, resp);

            appstateService.loadStateFromId(fakeHash);
            $httpBackend.flush();

            snapshot = makeFakeResponse(true); // create fake snapshot
            $httpBackend.expectGET(
                '/templates/main/appstate/share-appstate-dialog.html'
            ).respond(200, ''); // respond with empty template
            $httpBackend.expectPOST(
                '/api/appstates/' + fakeHash + '/snapshots'
            ).respond(200, snapshot); // respond with fake app state

            appstateService.shareState();
            $httpBackend.flush();

            expect($modal.open).toHaveBeenCalled();
        });
    });

});
