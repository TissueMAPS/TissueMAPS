var $injector;

describe('In MapObjectSelectionHandler', function() {
    beforeEach(module('tmaps.core'));

    beforeEach(inject(function(_$injector_) {
        $injector = _$injector_;
    }));

    var sh, vp;

    beforeEach(function() {
        vp = {};
        sh = new MapObjectSelectionHandler(vp);
    });

    describe('the function getSelectionsForType', function() {
        it('should return the selections for only a specific type', function() {
            pending();
        });
    });

    describe('the function addSelection', function() {
        it('should add a selection for some type', function() {
            pending();
        });
    });

    describe('the function clickOnMapObject', function() {
        it('should add an object to the active selection', function() {
            pending();
        });
    });

    describe('the function getActiveSelection', function() {
        it('should return the active selection if there is one', function() {
            pending();
        });
    });

    describe('the function getSelection', function() {
        it('should return the selection with some type and id if it exists', function() {
            pending();
        });
    });

    describe('the function addNewMapObjectSelection', function() {
        it('should add a new selection for the active type', function() {
            pending();
        });

        it('should automatically select a not-used color', function() {
            pending();
        });
    });

    describe('the function removeSelection', function() {
        it('should remove a selection from the map', function() {
            pending();
        });

        it('should remove the selection from the handler itself', function() {
            pending();
        });
    });

    describe('the function serialize', function() {
        it('should serialize the selection handler', function() {
            pending();
        });
    });

});
