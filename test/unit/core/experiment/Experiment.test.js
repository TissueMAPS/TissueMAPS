var $injector;

describe('In class Experiment', function() {
    beforeEach(module('tmaps.core'));

    var $httpBackend;
    var $rootScope;

    beforeEach(inject(function(_$injector_, _$httpBackend_, _$rootScope_) {
        $injector = _$injector_;
        $httpBackend = _$httpBackend_;
        $rootScope = _$rootScope_;
    }));

    var expArgs, exp, cellsResponse;

    beforeEach(function() {
        expArgs = {
            id: 'someId',
            name: 'SomeExp',
            description: 'bla',
            channels: []
        };

        cellsResponse = {
            1: [[0, 0], [0, 0], [0, 0], [0, 0]],
            2: [[0, 0], [0, 0], [0, 0], [0, 0]],
            3: [[0, 0], [0, 0], [0, 0], [0, 0]],
        };
    });

    beforeEach(function() {
        $httpBackend.whenGET('/api/experiments/' + expArgs.id + '/cells')
        .respond(200, cellsResponse);
        $httpBackend.whenGET('/api/experiments/' + expArgs.id +
            '/features?include=min,max')
        .respond(200, {});
    });

    describe('when creating the object', function() {
        it('should fetch the cells from the server', function() {
            $httpBackend.expectPOST('/api/experiments/' + expArgs.id + '/cells')
            .respond(200, cellsResponse);

            exp = new Experiment(expArgs);
        });

        it('should fetch the features', function() {
            $httpBackend.expectGET('/api/experiments/' + expArgs.id +
                '/features')
            .respond(200, {});

            exp = new Experiment(expArgs);
        });

        it('should create a map from cell ids to cells', function(done) {
            exp = new Experiment(expArgs);
            $httpBackend.flush();

            expect(exp.cellMap).toBeDefined();
            exp.cellMap.then(function(cellMap) {
                expect(cellsResponse[1]).toBeDefined();
                expect(cellsResponse[2]).toBeDefined();
                expect(cellsResponse[3]).toBeDefined();
                done();
            });

            $rootScope.$apply();
        });
    });

    describe('the function serialize', function() {
        it('should save the experiment', function() {
            exp = new Experiment(expArgs);

            exp.serialize().then(function(ser) {
                expect(ser.id).toEqual(exp.id);
                expect(ser.name).toEqual(exp.name);
                expect(ser.description).toEqual(exp.description);
                expect(ser.channels).toEqual(exp.channels);
            });

            $rootScope.$apply();
        });
    });
});
