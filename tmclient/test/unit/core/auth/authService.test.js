// describe('authService:', function() {

//     var authService, AUTH_EVENTS, $rootScope, $q, $httpBackend, authRequestHandler;

//     var dummyToken = "eyJhbGciOiJIUzI1NiIsImV4cCI6MTQzMDI1NDk3OCwiaWF0IjoxNDMwMjUzMTc4fQ.eyJ1bmFtZSI6InRlc3R1c2VyIiwidXJvbGVzIjpbInVzZXIiXSwidWlkIjoxLCJleHAiOjE0MzAyNTQ5Nzh9.dH5vnEUUGRRyL6zNFrrrkWdBi5EfOWhIQd4xh3FVUp8";

//     // Set up the module
//     beforeEach(module('tmaps.main.auth'));

//     beforeEach(inject(function(_authService_, _AUTH_EVENTS_, _$rootScope_, _$q_, _$httpBackend_) {
//         authService = _authService_;
//         AUTH_EVENTS = _AUTH_EVENTS_;
//         $rootScope = _$rootScope_;
//         $q = _$q_;
//         $httpBackend = _$httpBackend_;

//         // monitor a method on an object
//         spyOn($rootScope, '$broadcast');
//     }));

//     describe('The login function', function() {

//         it('exists', function() {
//             expect(authService.login).toBeDefined();
//         });

//         it('broadcasts AUTH_EVENTS.loginSuccess after successful login', function() {
//             $httpBackend.expectPOST('/auth').respond(200, { token: dummyToken });

//             authService.login('testuser', '123');
//             $httpBackend.flush(); // important, perform all requests

//             expect($rootScope.$broadcast).toHaveBeenCalledWith(AUTH_EVENTS.loginSuccess);
//         });

//         it('broadcasts AUTH_EVENTS.loginFailed after login failure', function() {
//             $httpBackend.expectPOST('/auth').respond(400);

//             authService.login('testuser', '123');
//             $httpBackend.flush();

//             expect($rootScope.$broadcast).toHaveBeenCalledWith(AUTH_EVENTS.loginFailed);
//         });
//     });

// });
