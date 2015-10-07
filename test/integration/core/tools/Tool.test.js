describe('In Tool', function() {
    var http, flush;

    beforeEach(function() {
        var i = angular.injector(['ng']),
            rs = i.get('$rootScope');
        http = i.get('$http');

        flush = function() {
            rs.$apply();
        };

        module('tmaps.core', function ($provide) {
            $provide.value('$http', http);
            $provide.value('$rootScope', rs);
        });
    });

    describe('the function sendRequest', function() {
        it('should send a request of the right format', function() {
           pending();
        });

    });

});
