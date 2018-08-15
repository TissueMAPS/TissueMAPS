var $injector;

describe('In MapObject', function() {
    beforeEach(module('tmaps.core'));

    beforeEach(inject(function(_$injector_) {
        $injector = _$injector_;
    }));
    
    describe('the function getVisual', function() {
        it('should return the right Visual depending on the visualType', function() {
            var m = new MapObject(1, 'cell', 'polygon', {
                coordinates: [[0, 1], [0, 1]]
            });
            expect(m.getVisual().constructor.name).toEqual('PolygonVisual');
        });
        
        
    });
    
    
});
