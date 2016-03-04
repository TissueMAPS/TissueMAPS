interface AppInstanceOpts {
    active: boolean;
}

interface SerializedAppInstance extends Serialized<AppInstance> {
    experiment: SerializedExperiment;
    viewport: SerializedViewport;
}

// TODO: Rename to Viewer
class AppInstance implements Serializable<SerializedAppInstance> {
    id: string;
    name: string;
    experiment: Experiment;
    viewport: Viewport;
    private _element: JQuery = null;
    private _active: boolean;

    // TODO: These properties might be better located on the Experiment class itself
    mapObjectRegistry: MapObjectRegistry;
    featureManager: FeatureManager;

    mapObjectSelectionHandler: MapObjectSelectionHandler;
    tools: ng.IPromise<Tool[]>;

    constructor(experiment: Experiment, opt?: AppInstanceOpts) {
        console.log('Creating AppInstance for Experiment with ID: ', experiment.id);
        console.log('This Experiment can be added automatically by visiting:\n',
                    'http://localhost:8002/#/viewport?loadex=' + experiment.id);
        var options: AppInstanceOpts = opt === undefined ? <AppInstanceOpts> {} : opt;
        this.id = makeUUID();
        this.experiment = experiment;
        this.name = experiment.name;
        this.viewport = new Viewport();
        this.viewport.injectIntoDocumentAndAttach(this);
        this.tools = this._loadTools();
        this.active = options.active === undefined ? false : options.active;

        this.featureManager = new FeatureManager(experiment);
        this.mapObjectRegistry = new MapObjectRegistry(experiment);

        this.mapObjectSelectionHandler = new MapObjectSelectionHandler(this.viewport, this.mapObjectRegistry);
        this.mapObjectRegistry.mapObjectTypes.then((types) => {
            _(types).each((t) => {
                this.mapObjectSelectionHandler.addMapObjectType(t);
                // Add an initial selection for the newly added type
                this.mapObjectSelectionHandler.addNewSelection(t);
            });
        });

        this._addExperimentToViewport();
    }

    private _addExperimentToViewport() {
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

    private _loadTools() {
        // TODO: Get tools from server (specific for user)
        var $q = $injector.get<ng.IQService>('$q');
        return $q.when([
            // new FeatureStatsTool(this),
            // new ScatterPlotTool(this),
            // new SVMTool(this),
            new ClusterTool(this)
        ]);
    }

    set active(active: boolean) {
        if (active) {
            this._showViewer();
        } else {
            this._hideViewer();
        }
        this._active = active;
    }

    get active() {
        return this._active;
    }

    destroy() {
        var elem = this._getDOMElement();
        elem.remove();
    }

    private _getDOMElement(): JQuery {
        if (this._element === null || this._element.length == 0) {
            var $document = $injector.get<ng.IDocumentService>('$document');
            this._element = $document.find('#viewer-'+ this.id);
        }
        return this._element;
    }

    private _hideViewer() {
        this._getDOMElement().hide();
    }

    private _showViewer() {
        this._getDOMElement().show();
        this.viewport.update();
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
