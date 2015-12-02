var $injector;

describe('In MapObjectManager', function() {
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
                ids: [1, 2],
                visualType: 'polygon',
                map_data: {
                    coordinates: {
                        1: [[1, 0], [1, 0]],
                        2: [[1, 0], [1, 0]]
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
        m = new MapObjectManager(fakeExp);
        $rootScope.$apply();
        $httpBackend.flush();
    });

    describe('the function getMapObjectsById', function() {
        it('should return the map objects requested', function() {
            pending();
            // m.getMapObjectsById
        });
    });

    describe('the function getMapObjectsByType', function() {
        it('should return the map objects requested', function(done) {
            m.getMapObjectsByType('cells').then(function(objs) {
                expect(objs[0].id).toEqual(1);
                expect(objs[1].id).toEqual(2);
                done();
            });
            $rootScope.$apply();
        });
    });
});
