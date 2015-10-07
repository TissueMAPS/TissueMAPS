describe('In EchoResultHandler', function() {
    var rh;

    beforeEach(function() {
        rh = new EchoResultHandler();
        console.log = jasmine.createSpy('log');
    });

    describe('the function handle', function() {
        var res = {
            message: 'o hai'
        };

        it('should do just log the message', function() {
            rh.handle(res);

            expect(console.log).toHaveBeenCalledWith(res);
        });

    });
});
