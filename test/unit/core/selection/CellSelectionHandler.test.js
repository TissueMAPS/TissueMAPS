var $injector;

describe('In CellSelectionHandler', function() {
    beforeEach(module('tmaps.core'));

    beforeEach(inject(function(_$injector_) {
        $injector = _$injector_;
    }));

    beforeEach(function() {
        selHandler = new CellSelectionHandler();
    });

    describe('the function addCellOutlines', function() {
        it('should add a new object layer containing cells', function() {
            pending();
        });

        it('should add an initially invisible layer', function() {
            pending();
        });
    });
});
