interface SerializedAppInstance extends Serialized<AppInstance> {
    experiment: SerializedExperiment;
    viewport: SerializedViewport;
}

class AppInstance implements Serializable<SerializedAppInstance> {
    name: string;
    experiment: Experiment;
    viewport: Viewport;
    mapObjectManager: MapObjectManager;
    mapObjectSelectionHandler: MapObjectSelectionHandler;
    tools: ng.IPromise<Tool[]>;

    constructor(experiment: Experiment) {
        console.log('Creating AppInstance for Experiment with ID: ', experiment.id);
        console.log('This Experiment can be added automatically by visiting:\n',
                    'http://localhost:8002/#/viewport?loadex=' + experiment.id);
        this.experiment = experiment;
        this.name = experiment.name;
        this.viewport = new Viewport();
        this.viewport.injectIntoDocumentAndAttach(this);
        this.tools = $injector.get<ToolLoader>('toolLoader').loadTools(this);

        this.mapObjectManager = new MapObjectManager(experiment);
        this.mapObjectSelectionHandler = new MapObjectSelectionHandler(this.viewport, this.mapObjectManager);
        this.mapObjectManager.mapObjectTypes.then((types) => {
            _(types).each((t) => {
                this.mapObjectSelectionHandler.addMapObjectType(t);
                // Add an initial selection for the newly added type
                this.mapObjectSelectionHandler.addNewSelection(t);
            });
        });
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
    }

    serialize(): ng.IPromise<SerializedAppInstance> {
        return $injector.get<ng.IQService>('$q').all({
            experiment: this.experiment.serialize(),
            viewport: this.viewport.serialize()
        }).then((res: any) => {
            return res;
        });
    }
}
