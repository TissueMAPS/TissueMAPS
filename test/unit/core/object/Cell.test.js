var $injector;

describe('In Cell', function() {
    // Load the module of ObjectLayer and its dependencies
    beforeEach(module('tmaps.core'));

    // Injected services and factories
    var Color, Cell;

    beforeEach(inject(function(_Cell_, _$injector_, _Color_) {
        $injector = _$injector_;
        Cell = _Cell_;
        Color = _Color_;
    }));

    var cell;

    beforeEach(function() {
        cell = new Cell('1', [100, 200], [
            [0, 0],
            [0, 1],
            [1, 0],
            [1, 1]
        ]);

    });

    it('should return a PolygonVisual as its Visual', function() {
        expect(cell.getVisual).toBeDefined();

        var v = cell.getVisual();
        console.log(v);
    });

});
