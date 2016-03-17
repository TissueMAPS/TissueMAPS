describe('In VectorLayer', function() {
    // Load the module of ObjectLayer and its dependencies
    beforeEach(module('tmaps.core'));

    // Some fake data
    var v1, v2, visuals;

    beforeEach(inject(function() {
        // Some fake data (assign again before each test in case functions would
        // modifies their arguments).
        v1 = new PolygonVisual([
            [0, 0],
            [0, 1],
            [1, 1],
            [1, 0]
        ]);
        v2 = new PolygonVisual([
            [0, 0],
            [0, 1],
            [1, 1],
            [1, 0]
        ]);
        visuals = [v1, v2];
        console = jasmine.createSpyObj('console', ['log']);
    }));

    describe('the constructor', function() {
        it('will accept a visuals argument that will set the visuals', function() {
            var l = new VectorLayer('some layer', {
                visuals: visuals
            });

            expect(l._visuals.length).toEqual(2);
        })
    });

    describe('the function addVisuals', function() {
        var layer;

        beforeEach(function() {
            layer = new VectorLayer('Cell layer')
        });

        it('should add a feature to the openlayers layer', function() {
            layer.addVisuals(visuals);

            expect(layer._olLayer.getSource().getFeatures()[0]).toBeDefined();
            expect(layer._olLayer.getSource().getFeatures()[1]).toBeDefined();
            expect(layer._olLayer.getSource().getFeatures()[2]).toBeUndefined();
        });

        it('should add a feature to layer itself', function() {
            layer.addVisuals(visuals);

            expect(layer.visuals[0]).toEqual(visuals[0]);
            expect(layer.visuals[1]).toEqual(visuals[1]);
            expect(layer.visuals[2]).toBeUndefined();
        });

        it('should not add any undefined or null visuals', function() {
            visuals.push(null);
            visuals.push(undefined);
            layer.addVisuals(visuals);

            expect(layer.visuals[0]).toEqual(visuals[0]);
            expect(layer.visuals[1]).toEqual(visuals[1]);
            expect(layer.visuals[2]).toBeUndefined();
        });
    });

    describe('the function addVisual', function() {
        var layer;

        beforeEach(function() {
            layer = new VectorLayer('some layer')
        });

        it('should add a single MapVisual', function() {
            layer.addVisual(visuals[0]);

            expect(layer.visuals[0]).toEqual(visuals[0]);
            expect(layer.visuals[1]).toBeUndefined();
        });

        it('should issue a warning when an undefined or null object is added', function() {
            layer.addVisual(null);
            expect(console.log).toHaveBeenCalled();
        });
    });

    describe('the getter visuals', function() {
        it('should get the visuals', function() {
            var l = new VectorLayer('some layer', {
                visuals: visuals
            });

            expect(l.visuals).toEqual(visuals);
        });
    });
});

