interface SerializedAppInstance extends Serialized<AppInstance> {
    experiment: SerializedExperiment;
    viewport: SerializedViewport;
}

class AppInstance implements Serializable<SerializedAppInstance> {
    name: string;
    experiment: Experiment;
    viewport: Viewport;
    tools: ng.IPromise<Tool[]>;

    constructor(private $q: ng.IQService,
                private viewportFty: ViewportFactory,
                private objectLayerFactory: ObjectLayerFactory,
                private toolLoader: ToolLoader,
                private channelLayerFactory: ChannelLayerFactory,
                experiment: Experiment) {
        this.experiment = experiment;
        this.name = experiment.name;
        this.viewport = this.viewportFty.create();
        this.viewport.injectIntoDocumentAndAttach(this);
        this.tools = this.toolLoader.loadTools(this);
        window['appInst'] = this;
    }

    setActive() {
        this.viewport.show();
    }

    setInactive() {
        this.viewport.hide();
    }

    destroy() {
        this.viewport.destroy();
    }

    addExperimentToViewport() {
        var layerOpts = _(this.experiment.channels).map((ch) => {
            return {
                name: ch.name,
                imageSize: ch.imageSize,
                pyramidPath: ch.pyramidPath
            };
        });
        this.viewport.addChannelLayers(<TileLayerArgs[]>layerOpts);
        // this.experiment.cells.then((cells) => {
        //     var cellLayer = this.objectLayerFactory.create('Cells', {
        //         objects: cells,
        //         fillColor: 'rgba(255, 0, 0, 0)',
        //         strokeColor: 'rgba(255, 0, 0, 1)'
        //     });
        //     this.viewport.addObjectLayer(cellLayer);
        // });
    }

    serialize(): ng.IPromise<SerializedAppInstance> {
        return this.$q.all({
            experiment: this.experiment.serialize(),
            viewport: this.viewport.serialize()
        }).then((res: any) => {
            return res;
        });
    }
}

class AppInstanceFactory {
    static $inject = [
        '$q',
        'viewportFactory',
        'objectLayerFactory',
        'toolLoader',
        'channelLayerFactory'
    ];
    constructor(private $q,
                private viewportFactory,
                private objectLayerFactory,
                private toolLoader,
                private channelLayerFactory) {}

    create(e: Experiment): AppInstance {
        return new AppInstance(this.$q, this.viewportFactory, this.objectLayerFactory, this.toolLoader, this.channelLayerFactory, e);
    }
}
angular.module('tmaps.core').service('appInstanceFactory', AppInstanceFactory);
