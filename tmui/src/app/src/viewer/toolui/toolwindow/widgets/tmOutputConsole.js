// Copyright (C) 2016-2018 University of Zurich.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// angular.module('tmaps.toolwindow')
// .directive('tmOutputConsole', ['toolInstance', '$sce', function(toolInstance, $sce) {

//     return {
//         restrict: 'E',
//         templateUrl: '/templates/tools/widgets/tm-output-console.html',
//         link: function(scope, element, attrs) {
//             toolInstance.socket
//             .$on('log', function(data) {
//                 element.find('.messages').append(
//                     '<span class="entry">' +
//                         '<span class="sender">SERVER:</span>' +
//                         '<span class="message">' + data + '</span>' +
//                     '</span><br>'
//                 );
//             });

//             scope.$watch(
//                 function() {
//                     return element.find('.entry').length;
//                 },
//                 function(newVal, oldVal) {
//                     var msgContainer = element.find('.messages');
//                     msgContainer.animate({
//                         scrollTop: msgContainer.prop('scrollHeight')
//                     }, 100);
//                 }
//             );
//         },
//         controller: ['$scope', function($scope) {
//                 // var messages = [];
//             // toolInstance.socket
//             // .$on('log', function(data) {
//             //     essages.push(data);
//             // });

//             // $scope.getMessages = function() {
//             //     return $sce.trustAsHtml(messages.join('<br>'));
//             // };
//         }]
//     };

// }]);
