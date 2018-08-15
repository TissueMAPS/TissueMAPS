var $injector

describe('In class PolygonVisual', function() {
    beforeEach(module('tmaps.core'));

    var pv;
    var coords;

    beforeEach(inject(function(_$injector_) {
        $injector = _$injector_;
        coords = [
            [0, 0],
            [0, -1],
            [1, -1],
            [1, 0],
            [0, 0]
        ];

        pv = new PolygonVisual(coords);
    }));

    it('should have a settable fillColor', function() {
        expect(pv.fillColor).toBeDefined();

        pv.fillColor = Color.RED;
        expect(pv.fillColor).toEqual(Color.RED);
    });
    
    it('should have a settable strokeColor', function() {
        expect(pv.fillColor).toBeDefined();

        pv.strokeColor = Color.RED;
        expect(pv.strokeColor).toEqual(Color.RED);
    });

    it('should by default have a white stroke color', function() {
        expect(pv.strokeColor).toEqual(Color.WHITE);
    });

    it('should by default have a red fill color', function() {
        expect(pv.fillColor).toEqual(Color.RED);
    });

    it('should accept fill and stroke colors as constructor arguments', function() {

        pv2 = new PolygonVisual(coords, {
            fillColor: Color.GREEN,
            strokeColor: Color.BLUE
        });
        expect(pv2.fillColor).toEqual(Color.GREEN);
        expect(pv2.strokeColor).toEqual(Color.BLUE);
    });
    
});
