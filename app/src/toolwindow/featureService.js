// angular.module('tmaps.toolwindow')
// .service('featureService', ['$http', '$q', function($http, $q) {

//     var features = {};

//     this.getForExperiment = function(id) {
//         if (!angular.isDefined(features[id])) {
//             var def = $q.defer();

//             $http.get('/experiments/' + id + '/features?include=min,max')
//             .success(function(data) {
//                 features[id] = [];
//                 console.log(data);
//                 _(data.features).each(function(feat) {
//                     features[id].push(feat);
//                 });
//                 def.resolve(features[id]);
//             });
//             return def.promise;
//         } else {
//             return $q.when(features[id]);
//         }
//     };
// }])

