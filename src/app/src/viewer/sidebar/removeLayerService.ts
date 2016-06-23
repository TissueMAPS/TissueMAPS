angular.module('tmaps.ui')
.service('removeLayerService', ['$modal', 'application', function($modal, app) {
    // Remove layers after warning.
    function removeAfterPrompt(layers, removalFunc) {
        var dialog = $modal.open({
            templateUrl: '/templates/main/layerprops/removelayer.html'
        });
        dialog.result.then(function(shouldRemove) {
            if (shouldRemove) {
                for (var i in layers) {
                    removalFunc(layers[i]);
                }
            }
        });
    }

    this.removeChannelsAfterPrompt = function(layers) {
        removeAfterPrompt(layers, function(l) {
            app.getActiveInstance().removeChannelLayer(l);
        });
    };
}]);

