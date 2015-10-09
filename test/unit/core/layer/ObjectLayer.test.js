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
        console = jasmine.createSpyObj('console', ['log']);
    }));

    describe('the constructor', function() {
        it('will accept an objects argument that will set the objects', function() {
            var l = new ObjectLayer('cellLayer', {
                objects: mapObjects
            });

            expect(l._objects.length).toEqual(2);
        })
    });

    describe('when creating the object', function() {
        it('should use a transparent color when the color is set to null', function() {
            var l = new ObjectLayer('cellLayer', {
                strokeColor: null,
                fillColor: null
            });

            expect(l.strokeColor.equals(new Color(0, 0, 0, 0))).toEqual(true);
            expect(l.fillColor.equals(new Color(0, 0, 0, 0))).toEqual(true);
        });

        it('should use the default color when the color is not provided (= undefined)', function() {
            var l = new ObjectLayer('cellLayer', {});

            expect(l.strokeColor.equals(l.defaultStrokeColor)).toEqual(true);
            expect(l.fillColor.equals(l.defaultFillColor)).toEqual(true);
        });
    });

    describe('the function addObjects', function() {
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

        it('should not add any undefined or null objects', function() {
            mapObjects.push(null);
            mapObjects.push(undefined);
            layer.addObjects(mapObjects);

            expect(layer.getObjects()[0]).toEqual(mapObjects[0]);
            expect(layer.getObjects()[1]).toEqual(mapObjects[1]);
            expect(layer.getObjects()[2]).toBeUndefined();
        });
    });

    describe('the function addObject', function() {
        var layer;

        beforeEach(function() {
            layer = new ObjectLayer('Cell layer')
        });

        it('should add a single MapObject', function() {
            layer.addObject(mapObjects[0]);

            expect(layer.getObjects()[0]).toEqual(mapObjects[0]);
            expect(layer.getObjects()[1]).toBeUndefined();
        });

        it('should not add any undefined or null objects', function() {
            layer.addObject(null);
            expect(layer.getObjects()[0]).toBeUndefined();
        });

        it('should issue a warning when an undefined or null object is added', function() {
            layer.addObject(null);
            expect(console.log).toHaveBeenCalled();
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

