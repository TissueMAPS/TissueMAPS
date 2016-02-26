interface SerializedAppInstance extends Serialized<AppInstance> {
    experiment: SerializedExperiment;
    viewport: SerializedViewport;
}

class AppInstance implements Serializable<SerializedAppInstance> {
    name: string;
    experiment: Experiment;
    viewport: Viewport;

    // TODO: These properties might be better located on the Experiment class itself
    mapObjectRegistry: MapObjectRegistry;
    featureManager: FeatureManager;

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
        this.tools = this._loadTools();

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

    private _loadTools() {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var toolsDef = $q.defer();
        $http.get('/src/core/tools/tools.json').then((resp) => {
            var toolsConfig = <any> resp.data;
            var classNames: string[] = toolsConfig.loadClasses;
            var tools = _.map(classNames, (clsName: string) => {
                var constr = window[clsName];
                if (constr === undefined) {
                    throw Error('No such tool constructor: ' + clsName);
                } else {
                    var t = new constr(this);
                    return t;
                }
                return t;
            });
            toolsDef.resolve(tools);
        });

        return toolsDef.promise;
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
