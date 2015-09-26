// var fakeLayerMod = {};
// var fakeInit = {
//     toolInstance: {
//         serverRepr: {

//         },
//         config: {

//         }
//     },
//     tmapsProxy: {
//         application: {},
//         viewport: {
//             addLayerMod: jasmine.createSpy('addLayerMod')
//         }
//     }
// };
// var fakeUrl = '/tools/' + fakeInit.toolInstance.config.toolId + '/instances/'
//               + fakeInit.toolInstance.serverRepr.id + '/request';

// describe('toolInstance', function() {

//     var toolInstance, $httpBackend, $rootScope, tmapsProxy;
//     var requesthandler;

//     beforeEach(function() {
//         module(function($provide) {
//             $provide.service('$window', function() {
//                 return {
//                     init: fakeInit,
//                     sessionStorage: {
//                         token: 'adfasdfasf'
//                     }
//                 };
//             });
//         });

//         module('tmaps.tools');

//         inject(function(_toolInstance_, _$httpBackend_, _$rootScope_, _tmapsProxy_) {
//             toolInstance = _toolInstance_;
//             $httpBackend = _$httpBackend_;
//             $rootScope = _$rootScope_;
//             tmapsProxy = _tmapsProxy_;
//         });

//         spyOn($rootScope, '$broadcast');

//         requestHandler = $httpBackend.expectPOST(fakeUrl, {
//             payload: {
//                 message: 'hi'
//             }
//         }).respond(200, {
//             return_value: {
//                 message: 'hello'
//             }
//         });
//     });

//     describe('its "sendRequest" function', function() {
//         it('should exist', function() {
//             expect(toolInstance.sendRequest).toBeDefined();
//         });

//         it('should broadcast events in the global scope when the request succeeds', function() {
//             toolInstance.sendRequest({
//                 message: 'hi'
//             });
//             $httpBackend.flush();

//             expect($rootScope.$broadcast).toHaveBeenCalledWith('toolRequestSent');
//             expect($rootScope.$broadcast).toHaveBeenCalledWith('toolRequestDone');
//             expect($rootScope.$broadcast).toHaveBeenCalledWith('toolRequestSuccess');
//         });

//         it('should broadcast events in the global scope when the request fails', function() {
//             requestHandler.respond(500, 'there was some error');

//             toolInstance.sendRequest({
//                 message: 'hi'
//             });
//             $httpBackend.flush();

//             expect($rootScope.$broadcast).toHaveBeenCalledWith('toolRequestSent');
//             expect($rootScope.$broadcast).toHaveBeenCalledWith('toolRequestDone');
//             expect($rootScope.$broadcast).toHaveBeenCalledWith('toolRequestFailed', 'there was some error');
//         });
//     });

// });
