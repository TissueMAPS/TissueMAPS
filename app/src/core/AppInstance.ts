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
                private colorFty: ColorFactory,
                private toolLoader: ToolLoader,
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
        _(layerOpts).each((opt, i) => {
            opt = _.defaults(opt, {
                visible: i === 0
            });
            var layer = new ChannelLayer(opt);
            this.viewport.addChannelLayer(layer);
        });

        this.experiment.cells.then((cells) => {
            var cellLayer = new ObjectLayer('Cells', {
                objects: cells,
                fillColor: Color.RED,
                strokeColor: Color.RED
            });
            this.viewport.addObjectLayer(cellLayer);
        });
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
        'colorFactory',
        'toolLoader',
    ];
    constructor(private $q,
                private viewportFactory,
                private colorFty,
                private toolLoader) {}

    create(e: Experiment): AppInstance {
        return new AppInstance(
            this.$q, this.viewportFactory,
            this.colorFty, this.toolLoader, e
        );
    }
}
angular.module('tmaps.core').service('appInstanceFactory', AppInstanceFactory);
