var $injector;

describe('In MapObjectSelectionHandler', function() {
    beforeEach(module('tmaps.core'));

    var $q;

    beforeEach(inject(function(_$injector_, _$q_) {
        $injector = _$injector_;
        $q = _$q_;
    }));

    var sh, vp;
    var sel1, sel2;
    var cell;
    var mapObjectRegistry;

    beforeEach(function() {
        vp = {
            map: jasmine.createSpyObj('map', ['then', 'on']),
            addVectorLayer: jasmine.createSpy('addVectorLayer')
        };
        mapObjectRegistry = {
            getMapObjectsForType: jasmine.createSpy('getMapObjectsForType').and.returnValue(
                $q.when()
            )
        };

        sh = new MapObjectSelectionHandler(vp, mapObjectRegistry);

        sh.addMapObjectType('cell');
        sh.addMapObjectType('nucleus');

        sel1 = new MapObjectSelection(0, 'cell', Color.RED);
        sel2 = new MapObjectSelection(0, 'nucleus', Color.BLUE);
        cell = {id: 1, type: 'cell'};
    });

    describe('the active MapObject type', function() {
        it('should be settable and gettable', function() {
            sh.activeMapObjectType = 'cell';
            expect(sh.activeMapObjectType).toEqual('cell');
        });

        it('should initially be set to the first object type added', function() {
            expect(sh.activeMapObjectType).toEqual('cell');
        });

        it('should initially be null and lead to 0 selections', function() {
            var sh2 = new MapObjectSelectionHandler(vp, mapObjectRegistry);
            expect(sh2.selectionsForActiveType).toEqual([]);
        });
    });

    describe('the function getSelectionsForType', function() {
        it('should return the selections for only a specific type', function() {
            sh.addSelection(sel1);

            expect(sh.getSelectionsForType(sel1.mapObjectType)[0]).toEqual(sel1);
        });

        it('should return an empty list if an object of unknown type is requested', function() {
            expect(sh.getSelectionsForType('some type')).toEqual([]);
        });
    });

    describe('the property selectionsForActiveType', function() {
       it('should provide all selections of the active type', function() {
            sh.addSelection(sel1);
            sh.activeMapObjectType = sel1.mapObjectType;

            expect(sh.selectionsForActiveType[0]).toEqual(sel1);
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
            sh.activeSelection = sel1;
            spyOn(sel1, 'addMapObject').and.callThrough();
            clickPos = {x: 10, y: 20};
        });
        
        it('should add an object to the active selection', function() {
            sh.activateMarkerSelectionMode();

            sh.clickOnMapObject(cell, clickPos);
            expect(sel1.addMapObject).toHaveBeenCalledWith(cell, clickPos);
            expect(sel1.isMapObjectSelected(cell)).toEqual(true);
        });

        it('should remove the object if it was already added', function() {
            sh.activateMarkerSelectionMode();

            sh.clickOnMapObject(cell, clickPos);
            expect(sel1.isMapObjectSelected(cell)).toEqual(true);
            sh.clickOnMapObject(cell, clickPos);
            expect(sel1.isMapObjectSelected(cell)).toEqual(false);
            sh.clickOnMapObject(cell, clickPos);
            expect(sel1.isMapObjectSelected(cell)).toEqual(true);
        });
        
        it('do nothing if selection mode isn\'t active', function() {
            sh.deactivateMarkerSelectionMode();

            sh.clickOnMapObject(cell, clickPos);
            expect(sel1.addMapObject).not.toHaveBeenCalled();
        });
        
    });

    describe('the property activeSelection', function() {
        it('should be settable and gettable', function() {
            sh.addSelection(sel1);
            sh.activeSelection = sel1;

            expect(sh.activeSelection).toEqual(sel1);
        });
    });

    describe('the property supportedMapObjectTypes', function() {
        it('should correspond to all types that are selectable', function() {
            sh.addSelection(sel1);

            expect(sh.supportedMapObjectTypes).toEqual(['cell', 'nucleus']);
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
            .toEqual(MapObjectSelection.availableColors[0]);
            expect(sh.getSelectionsForType('cell')[1].color)
            .toEqual(MapObjectSelection.availableColors[1]);
            expect(sh.getSelectionsForType('cell')[2].color)
            .toEqual(MapObjectSelection.availableColors[2]);

            sh.removeSelection(sel2);
            expect(sh.getSelectionsForType('cell').length).toEqual(2);

            // Assign the color that got freed up by removing sel2
            var newSel2 = sh.addNewSelection('cell');
            expect(sh.getSelectionsForType('cell')[2].color)
            .toEqual(MapObjectSelection.availableColors[1]);
        });

        it('should cycle colors when there are more selections than colors', function() {
            var nColors = MapObjectSelection.availableColors.length;
            for (var i = 0; i < 2 * nColors; i++) {
                sh.addNewSelection('cell');
            }
            expect(sh.getSelectionsForType('cell').length).toEqual(2 * nColors);
            for (var i = 0; i < nColors; i++) {
                expect(sh.getSelectionsForType('cell')[i + nColors].color)
                .toEqual(MapObjectSelection.availableColors[i]);
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
            sh.activeSelection = sel1;

            sh.removeSelection(sel1);

            expect(sh.activeSelection).toEqual(null);
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

    describe('the function addMapObjectType', function() {
        var sh3;

        beforeEach(function() {
            sh3 = new MapObjectSelectionHandler(vp, mapObjectRegistry);
            sh3.addMapObjectType('cell');
        });
        
        it('should add a new type', function() {
            expect(sh3.supportedMapObjectTypes).toEqual(['cell'])
        });

        it('should set the active type if not set already', function() {
            sh3.addMapObjectType('nuclei');
            expect(sh3.activeMapObjectType).toEqual('cell');
        });
    });
});
