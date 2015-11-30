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
        l = new MapObjectSelection('some selection');
    });

    it('should have a VisualLayer as a property', function() {
        expect(l._layer).toBeDefined();
    });

    describe('the function addToMap', function() {
        it('should add the map', function() {
            spyOn(l._layer, 'addToMap');
            var fakeMap = {};
            l.addToMap(fakeMap);
            expect(l._layer.addToMap).toHaveBeenCalledWith(fakeMap);
        });
    });

    describe('the function getMapObjects', function() {
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
            l.addMapObject(o);
            spyOn(l._layer, 'removeMapObjectMarker');
        });
        
        it('should remove the object from the selection', function() {
            expect(l.isMapObjectSelected(o)).toEqual(true);

            l.removeMapObject(o);

            expect(l.isMapObjectSelected(o)).toEqual(false);
        });
        
        it('should remove the object from the layer', function() {
            expect(l.isMapObjectSelected(o)).toEqual(true);
            l.removeMapObject(o);
            expect(l._layer.removeMapObjectMarker).toHaveBeenCalledWith(o.id);
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
            spyOn(l._layer, 'addMapObjectMarker');
        });
        
        it('should add a object if it was not added yet', function() {
            l.addMapObject(o);
            expect(l.isMapObjectSelected(o)).toEqual(true);
        });

        it('should not add a object twice', function() {
            l.addMapObject(o);
            l.addMapObject(o);

            expect(l.getMapObjects().length).toEqual(1);
        });
        
        it('should broadcast a `mapObjectSelectionChanged` event', function() {
            l.addMapObject(o);
            expect($rootScope.$broadcast).toHaveBeenCalledWith('mapObjectSelectionChanged', l);
        });

        it('should add a marker position if one was supplied', function() {
            var pos = {x: 10, y: 10};
            l.addMapObject(o, pos);

            expect(l._layer.addMapObjectMarker).toHaveBeenCalledWith(o.id, pos);
        });
    });

    describe('the function addRemoveMapObject', function() {
        var o;

        beforeEach(function() {
            o = {id: 1, type: 'cell'};
        });
        
        it('should add or remove the object depending on whether it\'s selected already', function() {
            expect(l.isMapObjectSelected(o)).toEqual(false);
            l.addRemoveMapObject(o);
            expect(l.isMapObjectSelected(o)).toEqual(true);
            l.addRemoveMapObject(o);
            expect(l.isMapObjectSelected(o)).toEqual(false);
        });
        
    });
    
});
