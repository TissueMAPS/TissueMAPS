angular.module('tmaps.tools.widgets')
.directive('tmOutputConsole', ['toolInstance', '$sce', function(toolInstance, $sce) {

    return {
        restrict: 'E',
        templateUrl: '/templates/tools/widgets/tm-output-console.html',
        link: function(scope, element, attrs) {
            toolInstance.socket
            .$on('log', function(data) {
                element.find('.messages').append(
                    '<span class="entry">' +
                        '<span class="sender">SERVER:</span>' +
                        '<span class="message">' + data + '</span>' +
                    '</span><br>'
                );
            });

            scope.$watch(
                function() {
                    return element.find('.entry').length;
                },
                function(newVal, oldVal) {
                    var msgContainer = element.find('.messages');
                    msgContainer.animate({
                        scrollTop: msgContainer.prop('scrollHeight')
                    }, 100);
                }
            );
        },
        controller: ['$scope', function($scope) {
                // var messages = [];
            // toolInstance.socket
            // .$on('log', function(data) {
            //     essages.push(data);
            // });

            // $scope.getMessages = function() {
            //     return $sce.trustAsHtml(messages.join('<br>'));
            // };
        }]
    };

}]);
