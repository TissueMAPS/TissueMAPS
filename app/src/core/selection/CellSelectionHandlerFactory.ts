class CellSelectionHandlerFactory {
    static $inject = [
        'cellSelectionFactory',
        '$q',
        '$http',
        '$rootScope'
    ];
    constructor(private cellSelectionFty: CellSelectionFactory,
                private $q,
                private $http: ng.IHttpService,
                private $rootScope: ng.IRootScopeService) {}

    create(viewport: Viewport) {
        return new CellSelectionHandler(
            this.cellSelectionFty,
            this.$q,
            this.$http,
            this.$rootScope,
            viewport
        );
    }
}

angular.module('tmaps.core')
.service('cellSelectionHandlerFactory', CellSelectionHandlerFactory);
