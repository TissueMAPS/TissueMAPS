var $injector;

describe('In Color', function() {
    beforeEach(module('tmaps.core'));

    var $rootScope;

    beforeEach(inject(function(_$injector_, _$rootScope_) {
        $injector = _$injector_;
        $rootScope = _$rootScope_;
    }));

    var color;
    var r, g, b, a;

    beforeEach(function() {
        r = 255;
        g = 50;
        b = 50;
        a = 1;
        color = new Color(r, g, b, a);
    });

    describe('for creating colors', function() {
        it('colors should be creatable from hex strings', function() {
            expect(Color.fromHex('FF00FF').equals(new Color(255, 0, 255))).toEqual(true);
        });

        it('colors should be creatable from normalized rgb arrays (as used by webgl)', function() {
            expect(Color.fromNormalizedRGBArray([1, 0, 1]).equals(new Color(255, 0, 255, 1))).toEqual(true);
        });

        it('colors should be creatable from rgb strings (as used by openlayers)',
        function() {
            expect(Color.fromRGBString('rgb(255, 0, 0)').equals(new Color(255, 0, 0))).toEqual(true);
            expect(Color.fromRGBString('rgb(255,      255,0)').equals(new Color(255, 255, 0))).toEqual(true);
            expect(Color.fromRGBString('rgb(255, 0)')).not.toBeDefined();
        });

        it('colors should be creatable from rgba objects (e.g. as output by "serialize")', function(done) {
            color.serialize().then(function(col) {
                expect(Color.fromObject(col).equals(color)).toEqual(true);
                done();
            })
            $rootScope.$apply();

            expect(Color.fromObject({r: 255, g: 0, b: 0}).equals(new Color(255, 0, 0, 1))).toEqual(true);
        });

        it('there should exist constants for multiple often used colors', function() {
            expect(Color.RED).toBeDefined();
            expect(Color.RED.equals(new Color(255, 0, 0))).toEqual(true);
            expect(Color.GREEN).toBeDefined();
            expect(Color.GREEN.equals(new Color(0, 255, 0))).toEqual(true);
            expect(Color.BLUE).toBeDefined();
            expect(Color.BLUE.equals(new Color(0, 0, 255))).toEqual(true);
            expect(Color.WHITE).toBeDefined();
            expect(Color.WHITE.equals(new Color(255, 255, 255))).toEqual(true);
            expect(Color.BLACK).toBeDefined();
            expect(Color.BLACK.equals(new Color(0, 0, 0))).toEqual(true);
        });
    });

    describe('the function toOlColor', function() {
        it('should convert the color into an openlayers color', function() {
            var ol = color.toOlColor();
            expect(ol).toEqual([r, g, b, a]);
        });
    });

    describe('the function toRGBAString', function() {
        it('should convert the color into an rgba string', function() {
            var c = color.toRGBAString();
            expect(c).toEqual('rgba(255, 50, 50, 1)');
        });
    });

    describe('the function toHex', function() {
        it('should convert the color into a hex string', function() {
            var h = (new Color(255, 0, 0)).toHex();
            expect(h).toEqual('#ff0000');

            var h = (new Color(255, 0, 255)).toHex();
            expect(h).toEqual('#ff00ff');

            var h = (new Color(0, 0, 0)).toHex();
            expect(h).toEqual('#000000');
        });
    });

    describe('the function toNormalizedRGBArray', function() {
        it('should convert the color to an array as used by webgl', function() {
            expect((new Color(0, 0, 0)).toNormalizedRGBArray()).toEqual([0, 0, 0]);
            expect((new Color(255, 0, 0)).toNormalizedRGBArray()).toEqual([1, 0, 0]);
            expect((new Color(255, 0, 255)).toNormalizedRGBArray()).toEqual([1, 0, 1]);
            expect((new Color(255, 0, 127.5)).toNormalizedRGBArray()).toEqual([1, 0, 0.5]);
        });
    });

    describe('the function equals', function() {
        it('should compare to colors', function() {
            expect((new Color(255, 0, 0)).equals(new Color(255, 0, 0))).toEqual(true);
            expect((new Color(255, 0, 0)).equals(new Color(255, 0, 0, 0.5))).toEqual(false);
            expect((new Color(255, 0, 0)).equals(new Color(255, 0, 255))).toEqual(false);
        });
    });

    describe('the function serialize', function() {
        it('should serialize the color', function() {
            color.serialize().then(function(col) {
                expect(col.r).toEqual(r);
                expect(col.g).toEqual(g);
                expect(col.b).toEqual(b);
                expect(col.a).toEqual(a);
            });
            $rootScope.$apply();
        });
    });

    describe('when modifying colors', function() {

        var col;
        beforeEach(function() {
            col = new Color(100, 100, 100, 1);
        });

        it('the color\'s red channel can be changed', function() {
            expect(col.withRed(255).equals(new Color(255, 100, 100, 1))).toEqual(true);
        });

        it('the color\'s green channel can be changed', function() {
            expect(col.withGreen(255).equals(new Color(100, 255, 100, 1))).toEqual(true);
        });

        it('the color\'s blue channel can be changed', function() {
            expect(col.withBlue(255).equals(new Color(100, 100, 255, 1))).toEqual(true);
        });

        it('the color\'s alpha channel can be changed', function() {
            expect(col.withAlpha(0).equals(new Color(100, 100, 100, 0))).toEqual(true);
        });

    });

});
