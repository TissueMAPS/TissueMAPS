class ViewportFactory {
    static $inject = [
        'openlayers',
        '$q',
        'cellSelectionHandlerFactory',
        'channelLayerFactory',
        '$http',
        'Cell',
        '$controller',
        '$compile',
        '$',
        '$document',
        '$rootScope'
    ];

    constructor(private ol,
                private $q: ng.IQService,
                private cellSelectionHandlerFty: CellSelectionHandlerFactory,
                private channelLayerFactory: ChannelLayerFactory,
                private $http: ng.IHttpService,
                private Cell,
                private $controller: ng.IControllerService,
                private $compile: ng.ICompileService,
                private $: JQueryStatic,
                private $document: ng.IDocumentService,
                private $rootScope: ng.IRootScopeService) {}

    create(): Viewport {
        return new Viewport(
            this.ol,
            this.$q,
            this.cellSelectionHandlerFty,
            this.channelLayerFactory,
            this.$http,
            this.Cell,
            this.$controller,
            this.$compile,
            this.$,
            this.$document,
            this.$rootScope
        );
    }
}
angular.module('tmaps.core').service('viewportFactory', ViewportFactory);

