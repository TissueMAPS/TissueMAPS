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
.service('cellSelectionHandlerFactory', CellSelectionHandlerFactory);
