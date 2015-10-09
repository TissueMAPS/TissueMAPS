describe('In ObjectLayer', function() {
    // Load the module of ObjectLayer and its dependencies
    beforeEach(module('tmaps.core'));

    // Some fake data
    var mapObject1, mapObject2, mapObjects;

    // Injected services and factories
    var Cell;

    beforeEach(inject(function(_Cell_) {
        // Assign to variables
        Cell = _Cell_;

        // Some fake data (assign again before each test in case functions would
        // modifies their arguments).
        mapObject1 = new Cell('cell1', {x: 100, y: -100});
        mapObject2 = new Cell('cell2', {x: 200, y: -100});
        mapObjects = [mapObject1, mapObject2];
    }));

    describe('the constructor', function() {
        it('will accept an objects argument that will set the objects', function() {
            var l = new ObjectLayer('cellLayer', {
                objects: mapObjects
            });

            expect(l._objects.length).toEqual(2);
        })
    });

    describe('the function addObject', function() {
        var layer;

        beforeEach(function() {
            layer = new ObjectLayer('Cell layer')
        });

        it('should add a feature to the openlayers layer', function() {
            layer.addObjects(mapObjects);

            expect(layer.olLayer.getSource().getFeatures()[0]).toBeDefined();
            expect(layer.olLayer.getSource().getFeatures()[1]).toBeDefined();
            expect(layer.olLayer.getSource().getFeatures()[2]).toBeUndefined();
        });

        it('should add a feature to layer itself', function() {
            layer.addObjects(mapObjects);

            expect(layer.getObjects()[0]).toEqual(mapObjects[0]);
            expect(layer.getObjects()[1]).toEqual(mapObjects[1]);
            expect(layer.getObjects()[2]).toBeUndefined();
        });
    });

    describe('the function getObjects', function() {
        it('should get the objects', function() {
            var l = new ObjectLayer('cellLayer', {
                objects: mapObjects
            });

            expect(l.getObjects()).toEqual(mapObjects);
        });
    });
});

