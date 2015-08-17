angular.module('tmaps.main').factory('uiState', function() {
    return {
        pressedKeys: {
            shift: false,
            alt: false,
            ctrl: false
        }
    };
});

