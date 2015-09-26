class ViewportFactory {
    static $inject = [
        'createViewportService',
        'openlayers',
        '$q',
        'cellSelectionHandlerFactory',
        'channelLayerFactory',
        'experimentFactory',
        '$http',
        'Cell',
        'objectLayerFactory',
        'toolLoader'
    ];

    constructor(private createViewportService: CreateViewportService,
                private ol,
                private $q: ng.IQService,
                private cellSelectionHandlerFty: CellSelectionHandlerFactory,
                private channelLayerFactory: ChannelLayerFactory,
                private experimentFactory: ExperimentFactory,
                private $http: ng.IHttpService,
                private Cell,
                private objectLayerFty: ObjectLayerFactory,
                private toolLoader: ToolLoader) {}

    create(experiment: Experiment): Viewport {
        return new Viewport(
            this.createViewportService,
            this.ol,
            this.$q,
            this.cellSelectionHandlerFty,
            this.channelLayerFactory,
            this.experimentFactory,
            this.$http,
            this.Cell,
            this.objectLayerFty,
            this.toolLoader,

            experiment
        );
    }
}
angular.module('tmaps.core').service('viewportFactory', ViewportFactory);

