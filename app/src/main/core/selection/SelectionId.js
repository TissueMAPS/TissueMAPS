angular.module('tmaps.core.selection')
.factory('SelectionId', [function() {

    function SelectionId(id) {
        this.id = id;
    }

    return SelectionId;
}]);
