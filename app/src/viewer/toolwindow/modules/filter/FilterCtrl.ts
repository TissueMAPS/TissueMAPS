// angular.module('tmaps.ui')
// .controller('FilterCtrl',
//             ['$scope', 'toolInstance',
//             function($scope, toolInstance) {

//     $scope.sendRequest = function() {
//         var payload = {
//             features: _($scope.selectedFeatures).map(function(feat) {
//                 return {
//                     name: feat.name,
//                     channel: feat.channel,
//                     range: feat.range
//                 };
//             })
//         };

//         toolInstance.sendRequest(payload).then(function(resp) {
//             console.log(resp);
//         });
//     };

// }]);

