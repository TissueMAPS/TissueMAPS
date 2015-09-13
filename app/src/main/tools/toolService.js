// angular.module('tmaps.main.tools')
// .service('toolService', ['$http', 'application', '$rootScope',
//          function($http, application, $rootScope) {

//     /**
//      * Ask the server to create tool instance.
//      */
//     function createToolInstance(tool, appstateId, experimentId) {
//         return $http
//         .post('/tools/' + tool.id + '/instances', {
//             'appstate_id': appstateId,
//             'experiment_id': experimentId
//         })
//         .then(
//         function(resp) {
//             console.log('Successfully created a tool instance.');
//             return resp.data;
//         },
//         function(err) {
//             console.log('Server refused to create a tool instance.', err);
//         });
//     }

//     /**
//      * Open a new browser window for this specific tool instance.
//      * Save some information on its root window object.
//      * Note that this window will have its own angular application.
//      */
//     this.openWindow = function(tool, appInstance, appstateId, experimentId) {
//         createToolInstance(tool, appstateId, experimentId)
//         .then(function(instance) {
//             // Without appending the current date to the title, the browser (chrome)
//             // won't open multiple tool windows of the same type.
//             var toolWindowCfg = tool.window || {};
//             var windowWidth = toolWindowCfg.width || 600;
//             var windowHeight = toolWindowCfg.height || 800;

//             var toolWindow = window.open(
//                 '/tools/#/' + tool.slug, tool.id, // + Date.now(),
//                 'toolbar=no,menubar=no,titebar=no,location=no,directories=no,replace=no,' +
//                 'width=' + windowWidth + ',height=' + windowHeight
//             );

//             if (_.isUndefined(toolWindow)) {
//                 throw new Error('Could not create tool window! Is your browser blocking popups?');
//             }

//             $(toolWindow).bind('beforeunload', function(event) {
//                 $http.delete('/tool_instances/' + instance.id)
//                 .then(function(resp) {
//                     console.log('Successfully deleted tool instance with id',
//                                 instance.id);
//                 }, function(err) {
//                     console.log('There was an error when trying to delete the',
//                                 'tool instance with ', instance.id, ':', err);
//                 });
//             });

//             // Create a container object that includes ressources that the tool may
//             // need.
//             var init = {
//                 tmapsProxy: {
//                     // The main application object
//                     application: application,
//                     // The appInstance from which this tool was called.
//                     // The map object is available via this object.
//                     appInstance: appInstance,
//                     // TissueMAPS' $rootScope; can be used to listen to
//                     // events that happen in the main window.
//                     $rootScope: $rootScope
//                 },
//                 toolInstance: {
//                     serverRepr: instance,
//                     config: tool
//                 }
//             };

//             // Save the initialization object to the local storage, such that the newly
//             // created window may retrieve it.
//             toolWindow.init = init;
//         });
//     };
// }]);
