var $injector: ng.auto.IInjectorService;

describe('In class Experiment', function() {

    beforeEach(inject(function(_$injector_) {
        $injector = _$injector_;
    }));

    it('should do something', function() {
        expect(true).toEqual(true);
    });
});
