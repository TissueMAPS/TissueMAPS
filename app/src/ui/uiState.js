angular.module('tmaps.ui').factory('uiState', function() {
    return {
        pressedKeys: {
            shift: false,
            alt: false,
            ctrl: false
        }
    };
});

