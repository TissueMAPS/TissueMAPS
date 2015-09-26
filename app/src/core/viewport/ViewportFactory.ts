class ViewportFactory {
    static $inject = [
        'createViewportService',
        'openlayers',
        '$q',
        'cellSelectionHandlerFactory',
        'channelLayerFactory',
        '$http',
        'Cell',
        'objectLayerFactory'
    ];

    constructor(private createViewportService: CreateViewportService,
                private ol,
                private $q: ng.IQService,
                private cellSelectionHandlerFty: CellSelectionHandlerFactory,
                private channelLayerFactory: ChannelLayerFactory,
                private $http: ng.IHttpService,
                private Cell,
                private objectLayerFty: ObjectLayerFactory) {}

    create(): Viewport {
        return new Viewport(
            this.createViewportService,
            this.ol,
            this.$q,
            this.cellSelectionHandlerFty,
            this.channelLayerFactory,
            this.$http,
            this.Cell,
            this.objectLayerFty
        );
    }
}
angular.module('tmaps.core').service('viewportFactory', ViewportFactory);

