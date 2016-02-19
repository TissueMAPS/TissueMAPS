var $injector;

describe('In MapObjectRegistry', function() {
    beforeEach(module('tmaps.core'));

    var $httpBackend, $rootScope, $q;

    beforeEach(inject(function(_$injector_, _$httpBackend_, _$rootScope_, _$q_) {
        $httpBackend = _$httpBackend_;
        $injector = _$injector_;
        $rootScope = _$rootScope_;
        $q = _$q_;
    }));
    
    var m, fakeExp;
    var objects;
    var handler;

    beforeEach(function() {
        objects = {
            'cells': {
                ids: [1, 2, 3],
                visual_type: 'polygon',
                map_data: {
                    coordinates: {
                        1: [[1, 0], [1, 0]],
                        2: [[1, 0], [1, 0]],
                        3: [[1, 0], [1, 0]]
                    }
                }
            }
        };
        handler = $httpBackend.expectGET('/api/experiments/somehash/objects')
        .respond(200, {
            objects: objects
        });
    });
    
    beforeEach(function() {
        fakeExp = {id: 'somehash'};
        m = new MapObjectRegistry(fakeExp);
        $rootScope.$apply();
        $httpBackend.flush();
    });

    describe('when creating the object', function() {
        it('should fetch the objects', function(done) {
            m.mapObjectsByType.then(function(objs) {
                expect(objs['cells']).toBeDefined();
                expect(_(objs['cells']).keys().length).toEqual(3);
                done();
            });
            $rootScope.$apply();
        });
    });

    describe('the function getMapObjectsById', function() {
        it('should return the map objects requested', function(done) {
            m.getMapObjectsById('cells', [1, 2]).then(function(res) {
                expect(res.length).toEqual(2);
                done();
            });
            $rootScope.$apply();
        });
    });

    describe('the function getMapObjectsForType', function() {
        it('should return the map objects requested', function(done) {
            m.getMapObjectsForType('cells').then(function(objs) {
                console.log('adjfhalksdhfasdkhfaklshdflk');
                expect(objs[1].id).toEqual(1);
                expect(objs[2].id).toEqual(2);
                done();
            });
            $rootScope.$apply();
        });
    });

    describe('the property mapObjectTypes', function() {
        it('should return the supported object types as a promise', function() {
            m.mapObjectTypes.then(function(types) {
                expect(_.intersection(types, ['cells']).length === 1).toEqual(true);
            });
            $rootScope.$apply();
        });
    });
});
