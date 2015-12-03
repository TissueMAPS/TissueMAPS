var $injector;

describe('In MapObjectSelectionHandler', function() {
    beforeEach(module('tmaps.core'));

    beforeEach(inject(function(_$injector_) {
        $injector = _$injector_;
    }));

    var sh, vp;
    var sel1, sel2;
    var cell;

    beforeEach(function() {
        vp = {};
        sh = new MapObjectSelectionHandler(vp);
        sh.addMapObjectType('cell');
        sh.addMapObjectType('nucleus');
        sel1 = new MapObjectSelection(0, 'cell', Color.RED);
        sel2 = new MapObjectSelection(0, 'nucleus', Color.BLUE);
        cell = {id: 1, type: 'cell'};

        sh.viewport.map = jasmine.createSpyObj('map', ['then']);
    });

    describe('the active MapObject type', function() {
        it('should be settable and gettable', function() {
            sh.setActiveMapObjectType('cell');
            expect(sh.getActiveMapObjectType()).toEqual('cell');
        });

        it('should initially be set to the first object type added', function() {
            expect(sh.getActiveMapObjectType()).toEqual('cell');
        });
    });

    describe('the function getSelectionsForType', function() {
        it('should return the selections for only a specific type', function() {
            sh.addSelection(sel1);

            expect(sh.getSelectionsForType(sel1.mapObjectType)[0]).toEqual(sel1);
        });

        it('should throw an error if an object of unknown type is requested', function() {
            var call = function() {
                sh.getSelectionsForType('some type');
            };
            expect(call).toThrowError();
        });
    });

    describe('the function addSelection', function() {
        it('should add a selection for the right type', function() {
            sh.addSelection(sel1);

            expect(sh.getSelectionsForType(sel1.mapObjectType)[0]).toEqual(sel1);
        });
    });

    describe('the function clickOnMapObject', function() {
        var clickPos;
        
        beforeEach(function() {
            sh.addSelection(sel1);
            sh.setActiveSelection(sel1);
            spyOn(sel1, 'addMapObject');
            clickPos = {x: 10, y: 20};
        });
        
        it('should add an object to the active selection', function() {
            pending();
            sh.activateMarkerSelectionMode();

            sh.clickOnMapObject(cell);
            expect(sel1.addMapObject).toHaveBeenCalledWith(cell, clickPos);
        });

        it('do nothing if selection mode isn\'t active', function() {
            sh.deactivateMarkerSelectionMode();

            sh.clickOnMapObject(cell);
            expect(sel1.addMapObject).not.toHaveBeenCalled();
        });
        
    });

    describe('the function getActiveSelection', function() {
        it('should return the active selection if there is one', function() {
            sh.addSelection(sel1);
            sh.setActiveSelection(sel1);

            var sel = sh.getActiveSelection();
            expect(sel).toEqual(sel1);
        });
    });

    describe('the function getSelection', function() {
        it('should return the selection with some type and id if it exists', function() {
            sh.addSelection(sel1);
            var sel = sh.getSelection(sel1.mapObjectType, sel1.id);
            expect(sel).toEqual(sel1);
        });
    });

    describe('the function addNewSelection', function() {
        it('should add a new selection for some type', function() {
            sh.addNewSelection('cell');
            expect(sh.getSelectionsForType('cell').length).toEqual(1);
        });

        it('should automatically select a not-used color', function() {
            var sel1 = sh.addNewSelection('cell');
            var sel2 = sh.addNewSelection('cell');
            var sel3 = sh.addNewSelection('cell');

            expect(sh.getSelectionsForType('cell')[0].color)
            .toEqual(sh.availableColors[0]);
            expect(sh.getSelectionsForType('cell')[1].color)
            .toEqual(sh.availableColors[1]);
            expect(sh.getSelectionsForType('cell')[2].color)
            .toEqual(sh.availableColors[2]);

            sh.removeSelection(sel2);
            expect(sh.getSelectionsForType('cell').length).toEqual(2);

            // Assign the color that got freed up by removing sel2
            var newSel2 = sh.addNewSelection('cell');
            expect(sh.getSelectionsForType('cell')[2].color)
            .toEqual(sh.availableColors[1]);
        });

        it('should cycle colors when there are more selections than colors', function() {
            var nColors = sh.availableColors.length;
            for (var i = 0; i < 2 * nColors; i++) {
                sh.addNewSelection('cell');
            }
            expect(sh.getSelectionsForType('cell').length).toEqual(2 * nColors);
            for (var i = 0; i < nColors; i++) {
                expect(sh.getSelectionsForType('cell')[i + nColors].color)
                .toEqual(sh.availableColors[i]);
            }
        });
        
        
    });

    describe('the function removeSelection', function() {
        it('should remove a selection from the map', function() {
            pending();
        });

        it('should remove the selection from the handler itself', function() {
            var sel1 = sh.addNewSelection('cell');
            expect(sh.getSelection('cell', sel1.id)).toBeDefined();

            sh.removeSelection(sel1);
            expect(sh.getSelection('cell', sel1.id)).not.toBeDefined();
        });

        it('should set the active selection to null if the selection to be removed was active', function() {
            var sel1 = sh.addNewSelection('cell');
            sh.setActiveSelection(sel1);

            sh.removeSelection(sel1);

            expect(sh.getActiveSelection()).toEqual(null);
        });
        
        
    });

    describe('the function serialize', function() {
        it('should serialize the selection handler', function() {
            pending();
        });
    });

    describe('the marker selection mode', function() {
        it('should be OFF by default', function() {
            expect(sh.isMarkerSelectionModeActive()).toBe(false);
        });
        
        it('should be activateable', function() {
            sh.activateMarkerSelectionMode();
            expect(sh.isMarkerSelectionModeActive()).toEqual(true);
        });

        it('should be deactivateable', function() {
            sh.deactivateMarkerSelectionMode();
            expect(sh.isMarkerSelectionModeActive()).toEqual(false);
        });
        
    });

});
