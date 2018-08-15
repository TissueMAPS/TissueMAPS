var $injector;

describe('In class Experiment', function() {
    beforeEach(module('tmaps.core'));

    var $httpBackend;
    var $rootScope;

    beforeEach(inject(function(_$injector_, _$httpBackend_, _$rootScope_) {
        $injector = _$injector_;
        $httpBackend = _$httpBackend_;
        $rootScope = _$rootScope_;
    }));

    var expArgs, exp;

    beforeEach(function() {
        expArgs = {
            id: 'someId',
            name: 'SomeExp',
            description: 'bla',
            channels: []
        };
    });

    describe('the function serialize', function() {
        it('should save the experiment', function() {
            exp = new Experiment(expArgs);

            exp.serialize().then(function(ser) {
                expect(ser.id).toEqual(exp.id);
                expect(ser.name).toEqual(exp.name);
                expect(ser.description).toEqual(exp.description);
                expect(ser.channels).toEqual(exp.channels);
            });

            $rootScope.$apply();
        });
    });
});
