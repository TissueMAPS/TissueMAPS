class CellSelectionHandlerFactory {
    static $inject = [
        'ColorFactory',
        'CellSelectionFactory',
        '$q',
        '$http',
        '$rootScope'
    ];
    constructor(private colorFty: ColorFactory,
                private cellSelectionFty: CellSelectionFactory,
                private $q,
                private $http,
                private $rootScope) {}

    create(appInstance: AppInstance) {
        return new CellSelectionHandler(
            this.colorFty,
            this.cellSelectionFty,
            this.$q,
            this.$http,
            this.$rootScope,
            appInstance
        );
    }
}

angular.module('tmaps.core.selection')
.service('CellSelectionHandlerFactory', CellSelectionHandlerFactory);
