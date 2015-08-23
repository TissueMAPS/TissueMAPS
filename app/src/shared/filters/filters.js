angular.module('tmaps.shared.filters', [])
.filter('reverse', function() {
    return function(items) {
      return items.slice().reverse();
    };
});
