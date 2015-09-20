// angular.module('tmaps.main.appstate')
// /**
//  * A service that concerns itself with querying the server
//  * for experiments and prompting to user when he wants to add an experiment
//  * to the viewport.
//  */
// .service('appstateService',
//          ['application', '$modal', '$http', '$q', '$location', '$state',
//              'applicatioDeserializer',
//              function(application, $modal, $http, $q, $location, $state,
//                  applicatioDeserializer) {

//     var self = this;

//     function setCurrentState(st) {
//         self.currentState = st;
//         if (st.isSnapshot) {
//             $location.search({'snapshot': st.id});
//         } else {
//             $location.search({'state': st.id});
//         }
//     }

//     function toClientRepresentation(st) {
//         return {
//             id: st.id,
//             name: st.name,
//             owner: st.owner,
//             isSnapshot: st.is_snapshot,
//             blueprint: st.blueprint
//         };
//     }

//     /**
//      * The currently active app state.
//      * be updated so that subsequent save requests will be performed on the
//      * If the application state is saved for the first time, this will
//      * current state.
//      */
//     this.currentState = {};

//     this.lastSavedAt;

//     this.stateHasBeenSavedAlready = function() {
//         return angular.isDefined(self.currentState.id);
//     };

//     /**
//      * Get all available app states for the current user.
//      */
//     this.getStates = function() {
//         return $http.get('/api/appstates').then(function(resp) {
//             var res = {
//                 owned: _(resp.data.owned).map(toClientRepresentation),
//                 shared: _(resp.data.shared).map(toClientRepresentation)
//             };
//             return res;
//         });
//     };

//     /**
//      * Load an app state into the application.
//      */
//     this.loadState = function(state) {
//         setCurrentState(state);
//         console.log('deser called');
//         applicatioDeserializer.deserialize(state.blueprint);
//     };

//     this.loadStateFromId = function(id) {
//         return $http
//         .get('/api/appstates/' + id).then(function(resp) {
//             return resp.data;
//         })
//         .then(
//             function(data) {
//                 var state = toClientRepresentation(data);
//                 self.loadState(state);
//                 return state;
//             },
//             function(resp, headers) {
//                 throw new Error(
//                     'Server-side error when trying to load state: ' +
//                     resp.status
//                 );
//             }
//         );
//     };

//     /*
//      * Query the server for a snapshot.
//      * This function is basically the same as the one for getting normal
//      * appstates but calls a different ressource on the server since
//      * snapshots have different access restrictions.
//      */
//     this.loadSnapshotFromId = function(id) {
//         return $http
//         .get('/snapshots/' + id).then(function(resp) {
//             return resp.data;
//         })
//         .then(
//             function(data) {
//                 var state = toClientRepresentation(data);
//                 setCurrentState(state);
//                 self.loadState(state);
//                 return state;
//             },
//             function(resp, headers) {
//                 throw new Error(
//                     'Server-side error when trying to load state: ' +
//                     resp.status
//                 );
//             }
//         );
//     };

//     /**
//      * Ask the server to update the current appstate with a new blueprint.
//      * If no app state is active, a 'Save as'-dialog will appear.
//      */
//     this.saveState = function() {
//         if (self.currentState.isSnapshot) {
//             throw new Error('Can\'t save snapshots!');
//         } else if (!self.stateHasBeenSavedAlready()) {
//             self.promptForSaveAs();
//         } else {
//             var id = self.currentState.id;
//             application.serialize()
//             .then(function(bp) {
//                 return $http.put('/api/appstates/' + id, {
//                     blueprint: bp
//                 });
//             })
//             .then(function(resp) {
//                 var state = toClientRepresentation(resp.data);
//                 setCurrentState(state);
//                 self.lastSavedAt = new Date();
//             })
//             .catch(function(err) {
//                 console.log('There was an error when trying to save app state.', err);
//             });
//         }
//     };

//     /**
//      * Popup a dialog where the user can enter a name and optional description
//      * for the appstate that has to be saved.
//      * TODO: Add validation to the dialog.
//      */
//     this.promptForSaveAs = function() {
//         var instance = $modal.open({
//             templateUrl: '/templates/main/appstate/save-appstate-as-dialog.html',
//             controller: 'SaveAppstateAsDialogCtrl',
//             controllerAs: 'dialog'
//         });

//         return instance.result.then(function(res) {
//             return self.saveStateAs(res.name, res.description);
//         });
//     };

//     /**
//      * Ask the server to save an appstate under a new name.
//      */
//     this.saveStateAs = function(name, description) {
//         if (self.currentState.isSnapshot) {
//             throw new Error('A snapshot can\'t be saved under a different name');
//         }
//         return application.serialize()
//         .then(function(bp) {
//             return $http.post('/api/appstates', {
//                 name: name,
//                 description: description,
//                 blueprint: bp
//             });
//         })
//         .then(function(resp) {
//             var state = toClientRepresentation(resp.data);
//             setCurrentState(state);
//             self.lastSavedAt = new Date();
//         }, function(err) {
//             console.log('There was an error when trying to save app state.', err);
//         });
//     };

//     // TODO: Currently only snapshot-sharing is enabled,
//     // Split this function into one for normal sharing and one for snapshot sharing
//     this.shareState = function() {
//         if (self.currentState.isSnapshot) {
//             throw new Error('A snapshot can\'t be shared again');
//         } else if (self.stateHasBeenSavedAlready()) {
//             var url = '/api/appstates/' + self.currentState.id + '/snapshots';
//             var instance = $modal.open({
//                 templateUrl: '/templates/main/appstate/share-appstate-dialog.html',
//                 controller: 'ShareAppstateCtrl',
//                 controllerAs: 'share',
//                 resolve: {
//                     link: ['$http', function($http) {
//                         return $http.post(url)
//                         .then(function(resp) {
//                             return self.getLinkForSnapshot(resp.data);
//                         });
//                     }]
//                 }
//             });
//         } else {
//             throw new Error('Appstate needs to be saved before it can be shared!');
//         }
//     };

//     this.getLinkForSnapshot = function(snapshot) {
//         var link = 'http://' + document.domain;
//         if (location.port !== 80) {
//             link += ':' + location.port;
//         }
//         link += '/#/viewport?snapshot=' + snapshot.id;
//         return link;
//     };

// }]);
