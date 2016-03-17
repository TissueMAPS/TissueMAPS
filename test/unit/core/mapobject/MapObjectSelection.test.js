var $injector;

describe('In MapObjectSelection', function() {
    // Load the module of ObjectLayer and its dependencies
    beforeEach(module('tmaps.core'));

    var l, $rootScope;

    beforeEach(inject(function(_$rootScope_, _$injector_) {
        $injector = _$injector_;
        $rootScope = _$rootScope_; 
        spyOn($rootScope, '$broadcast');
    }));

    beforeEach(function() {
        l = new MapObjectSelection('some selection', 'cell', Color.RED);
    });

    it('should have a VectorLayer as a property', function() {
        expect(l._layer).toBeDefined();
    });

    describe('the function visualizeOnViewport', function() {
        it('should add the map', function() {
            var viewport = jasmine.createSpyObj('viewport', ['addVectorLayer']);
            l.visualizeOnViewport(viewport);
            expect(viewport.addVectorLayer).toHaveBeenCalledWith(l._layer);
        });
    });

    describe('the property mapObjects', function() {
        it('should return the selected map objects', function() {
            pending();
        });
    });

    describe('the function removeFromMap', function() {
        beforeEach(function() {
            spyOn(l, 'clear');
            spyOn(l._layer, 'removeFromMap');
        });
        
        it('should remove the layer', function() {
            var fakeMap = {};
            l.removeFromMap(fakeMap);
            expect(l._layer.removeFromMap).toHaveBeenCalledWith(fakeMap);
        });

        it('should clear layer', function() {
            var fakeMap = {};
            l.removeFromMap(fakeMap);
            expect(l.clear).toHaveBeenCalled();
        });
    });

    describe('the function removeMapObject', function() {
        var o;

        beforeEach(function() {
            o = {id: 1, type: 'cell'};
            l.addMapObject(o, {x: 10, y: -10});
            spyOn(l._layer, 'removeVisual');
        });
        
        it('should remove the object from the selection', function() {
            expect(l.isMapObjectSelected(o)).toEqual(true);

            l.removeMapObject(o);

            expect(l.isMapObjectSelected(o)).toEqual(false);
        });
        
        it('should remove the object from the layer', function() {
            expect(l.isMapObjectSelected(o)).toEqual(true);
            l.removeMapObject(o);
            expect(l._layer.removeVisual).toHaveBeenCalled();
        });
        
        it('should should broadcast a `mapObjectSelectionChanged` event', function() {
            l.removeMapObject(o);

            expect($rootScope.$broadcast).toHaveBeenCalledWith('mapObjectSelectionChanged', l);
        });
    });

    describe('the function addMapObject', function() {
        var o;

        beforeEach(function() {
            o = {id: 1, type: 'cell'};
            spyOn(l._layer, 'addVisual');
        });
        
        it('should add a object if it was not added yet', function() {
            l.addMapObject(o, {x: 10, y: -10});
            expect(l.isMapObjectSelected(o)).toEqual(true);
        });

        it('should not add a object twice', function() {
            l.addMapObject(o, {x: 10, y: -10});
            l.addMapObject(o, {x: 10, y: -10});

            expect(l.mapObjects.length).toEqual(1);
        });
        
        it('should broadcast a `mapObjectSelectionChanged` event', function() {
            l.addMapObject(o, {x: 10, y: -10});
            expect($rootScope.$broadcast).toHaveBeenCalledWith('mapObjectSelectionChanged', l);
        });

        it('should add a marker icon', function() {
            l.addMapObject(o, {x: 10, y: -10});

            expect(l._layer.addVisual).toHaveBeenCalled();
        });
    });

    describe('the function addRemoveMapObject', function() {
        var o;

        beforeEach(function() {
            o = {id: 1, type: 'cell'};
        });
        
        it('should add or remove the object depending on whether it\'s selected already', function() {
            var pos = {x: 10, y: -10};
            expect(l.isMapObjectSelected(o)).toEqual(false);
            l.addRemoveMapObject(o, pos);
            expect(l.isMapObjectSelected(o)).toEqual(true);
            l.addRemoveMapObject(o, pos);
            expect(l.isMapObjectSelected(o)).toEqual(false);
        });
        
    });
    
});
