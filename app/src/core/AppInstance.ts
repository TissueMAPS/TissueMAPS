interface SerializedAppInstance extends Serialized<AppInstance> {
    experiment: SerializedExperiment;
    viewport: SerializedViewport;
}

class AppInstance implements Serializable<SerializedAppInstance> {
    name: string;
    experiment: Experiment;
    viewport: Viewport;
    tools: ng.IPromise<Tool[]>;

    constructor(experiment: Experiment) {
        this.experiment = experiment;
        this.name = experiment.name;
        this.viewport = new Viewport();
        this.viewport.injectIntoDocumentAndAttach(this);
        this.tools = $injector.get<ToolLoader>('toolLoader').loadTools(this);
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
            this.viewport.selectionHandler.addCellOutlines(cells);
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
