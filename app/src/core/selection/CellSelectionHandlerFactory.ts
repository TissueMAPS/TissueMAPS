class CellSelectionHandlerFactory {
    static $inject = [
        'colorFactory',
        'cellSelectionFactory',
        '$q',
        '$http',
        '$rootScope'
    ];
    constructor(private colorFty: ColorFactory,
                private cellSelectionFty: CellSelectionFactory,
                private $q,
                private $http: ng.IHttpService,
                private $rootScope: ng.IRootScopeService) {}

    create(viewport: Viewport) {
        return new CellSelectionHandler(
            this.colorFty,
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
