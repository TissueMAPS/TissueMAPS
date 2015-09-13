class AppInstanceFactory {
    static $inject = [
        'CreateViewportService',
        'openlayers',
        '$q',
        'CellSelectionHandler',
        'CycleLayerFactory',
        'OutlineLayerFactory',
        'ExperimentFactory',
        '$http',
        'Cell',
        'ObjectLayerFactory',
        'ToolLoader'
    ];

    constructor(private CreateViewportService,
                private ol,
                private $q,
                private CellSelectionHandler,
                private CycleLayerFactory,
                private OutlineLayerFactory,
                private ExperimentFactory,
                private $http,
                private Cell,
                private ObjectLayerFactory,
                private ToolLoader) {}

    create(experiment: Experiment): AppInstance {
        return new AppInstance(
            this.CreateViewportService,
            this.ol,
            this.$q,
            this.CellSelectionHandler,
            this.CycleLayerFactory,
            this.OutlineLayerFactory,
            this.ExperimentFactory,
            this.$http,
            this.Cell,
            this.ObjectLayerFactory,
            this.ToolLoader,

            experiment
        );
    }
}
angular.module('tmaps.core').service('AppInstanceFactory', AppInstanceFactory);

