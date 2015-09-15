interface MapState {
    zoom: number;
    center: ol.Coordinate;
    resolution: number;
    rotation: number;
}

interface SerializedAppInstance extends Serialized<AppInstance> {
    experiment: SerializedExperiment;
    selectionHandler: SerializedSelectionHandler;
    channelLayerOptions: TileLayerArgs;
    maskLayerOptions: TileLayerArgs;
    mapState: MapState;
}

class AppInstance implements Serializable<AppInstance> {

    experiment: Experiment;
    viewport: ng.IPromise<Viewport>;
    map: ng.IPromise<ol.Map>;

    cycleLayers: CycleLayer[] = [];
    outlineLayers: OutlineLayer[] = [];
    objectLayers: ObjectLayer[] = [];

    selectionHandler: CellSelectionHandler;

    tools: ng.IPromise<Tool[]>;

    constructor(private createViewportService: CreateViewportService,
                private ol,
                private $q: ng.IQService,
                private cellSelectionHandlerFty: CellSelectionHandlerFactory,
                private cycleLayerFactory: CycleLayerFactory,
                private outlineLayerFactory: OutlineLayerFactory,
                private experimentFactory: ExperimentFactory,
                private $http: ng.IHttpService,
                private Cell,
                private objectLayerFactory: ObjectLayerFactory,
                private toolLoader: ToolLoader,

                experiment: Experiment) {

        this.experiment = experiment;

        var mapDef = $q.defer();
        this.map = mapDef.promise;

        var viewportDef = $q.defer();
        this.viewport = viewportDef.promise;

        // Helper class to manage the differently marker selections
        this.selectionHandler = this.cellSelectionHandlerFty.create(this);

        createViewportService.createViewport(
            this, 'viewports', '/templates/main/viewport.html'
        ).then(function(viewport) {
            viewportDef.resolve(viewport);
            mapDef.resolve(viewport.map);
        });

        // Load tools
        this.tools = this.toolLoader.loadTools(this);


        var createDemoRectangles = function(startx, starty) {
            var side = 100;
            var nRect = 100;
            var cells = [];
            for (var i = startx; i <  side * nRect + startx; i += side) {
                for (var j = starty; j < side * nRect + starty; j += side) {
                    var coords = [[
                        [i, -j],
                        [i + side, -j],
                        [i + side, -j - side],
                        [i, -j - side],
                        [i, -j]
                    ]];
                    var c = new this.Cell('bla', {x: i, y: -j}, coords);
                    cells.push(c);
                }
            }
            return cells;
        }

        var cellsA = createDemoRectangles(0, 0);
        var cellsB = createDemoRectangles(10000, 0);

        var objLayerA = this.objectLayerFactory.create('Cells A', {
            objects: cellsA,
            fillColor: 'rgba(0, 0, 255, 0.5)',
            strokeColor: 'rgba(0, 0, 255, 1)'
        });
        var objLayerB = this.objectLayerFactory.create('Cells B', {
            objects: cellsB,
            fillColor: 'rgba(255, 0, 0, 0.5)',
            strokeColor: 'rgba(255, 0, 0, 1)'
        });

        this.addObjectLayer(objLayerA);
        this.addObjectLayer(objLayerB);
    }

    addObjectLayer(objLayer: ObjectLayer) {
        this.objectLayers.push(objLayer);
        this.map.then((map) => {
            objLayer.addToMap(map);
        });
    }

    removeObjectLayer(objLayer: ObjectLayer) {
        var idx = this.objectLayers.indexOf(objLayer)
        if (idx !== -1) {
            this.map.then((map) => {
                objLayer.removeFromMap(map);
                this.objectLayers.splice(idx, 1);
            });
        }
    }

    // TODO: Consider throwing everything cell position related into own
    // CellPositionHandler or something like that.
    getCellAtPos(pos: MapPosition) {
        return this.$http.get(
            '/experiments/' + this.experiment.id +
            '/cells?x=' + pos.x + '&y=' + pos.y
        ).then((resp) => {
            console.log(resp);
            return resp.data['cell_id'];
        });
    }

    addChannelLayers(layerOptions) {
        // Only the first layer should be visible
        _.each(layerOptions, (opt, i) => {
            opt = _.defaults(opt, {
                visible: i === 0,
                color: [1, 1, 1]
            });
            this.addCycleLayer(opt);
        });
    }

    /*
     * Add a cycle layer to the underlying map object
     * Always use this smethod when adding new cycles.
     */
    addCycleLayer(opt) {
        var cycleLayer = this.cycleLayerFactory.create(opt);
        var alreadyHasLayers = this.cycleLayers.length !== 0;

        // If this is the first time a layer is added, create a view and add it to the map.
        if (!alreadyHasLayers) {
            // Center the view in the iddle of the image
            // (Note the negative sign in front of half the height)
            var width = opt.imageSize[0];
            var height = opt.imageSize[1];
            var center = [width / 2, - height / 2];
            var view = new this.ol.View({
                // We create a custom (dummy) projection that is based on pixels
                projection: new this.ol.proj.Projection({
                    code: 'ZOOMIFY',
                    units: 'pixels',
                    extent: [0, 0, width, height]
                }),
                center: center,
                zoom: 0, // 0 is zoomed out all the way
                // starting at maxResolution where maxResolution
                // is

            });

            this.map.then(function(map) {
                map.setView(view);
            });
        }

        // Add the layer as soon as the map is created (i.e. resolved after
        // viewport injection)
        this.map.then(function(map) {
            cycleLayer.addToMap(map);
        });
        this.cycleLayers.push(cycleLayer);
    }

    /**
     * Remove a cycleLayer from the map.
     * Use this method whenever a layer should be removed since it also updates
     * the app instance's internal state.
     */
    removeCycleLayer(cycleLayer) {
        this.map.then(function(map) {
            cycleLayer.removeFromMap(map);
        });
        var idx = this.cycleLayers.indexOf(cycleLayer);
        this.cycleLayers.splice(idx, 1);
    }


    addMaskLayers(layerOptions) {
        // Add the layers that are flagged as masking layers
        // If there are multiple such layers, the first will be
        // initially visible and the others invisible.
        _.each(layerOptions, (opt, i) => {
            opt = _.defaults(opt, {
                visible: i === 0,
                color: [1, 1, 1]
            });
            this.addOutlineLayer(opt);
        });
    }

    /*
     * Add a segmentation layer for this experiment
     * The main difference to setting a cycle layer is that
     * 1. The created class is a OutlineLayer and as such it is not blended
     *    additively but black parts of the image aren't drawn anyway.
     * 2. The layer won't get added to the AppInstance.cycleLayers array.
     */
    addOutlineLayer(opt) {
        var outlineLayer = this.outlineLayerFactory.create(opt);
        this.outlineLayers.push(outlineLayer);

        return this.map.then(function(map) {
            outlineLayer.addToMap(map);
            return outlineLayer;
        });
    }

    /**
     * Remove a outlineLayer from the map.
     * Use this method whenever a layer should be removed since it also updates
     * the app instance's internal state.
     */
    removeOutlineLayer(outlineLayer) {
        this.map.then(function(map) {
            outlineLayer.removeFromMap(map);
        });
        var idx = this.outlineLayers.indexOf(outlineLayer);
        this.outlineLayers.splice(idx, 1);
    }



    /**
     * Clean up method when the instance is closed (e.g. by deleting the Tab).
     */
    destroy() {
        this.viewport.then((viewport) => {
            // Destroy the stuff that this instance created
            viewport.scope.$destroy();
            viewport.element.remove();
        });
    }

    /**
     * Set this instance active: display the map container and handle the case
     * when the browser window was resized.
     * NOTE: Always call the setActiveInstance method on the application global
     * object since that function will also deactivate other instances.
     */
    setActive() {
        this.viewport.then(function(viewport) {
            viewport.element.show();
            viewport.map.updateSize();
        });
    }

    /**
     * Hide the openlayers canvas.
     * As with setInactive: the Application object should call this function
     * and make sure that exactly one AppInstance is set active at all times.
     */
    setInactive() {
        this.viewport.then(function(viewport) {
            viewport.element.hide();
        });
    }


    serialize() {
        var bpPromise = this.map.then((map) => {
            var v = map.getView();

            var mapState = {
                zoom: v.getZoom(),
                center: v.getCenter(),
                resolution: v.getResolution(),
                rotation: v.getRotation()
            };

            var channelOpts = _(this.cycleLayers).map(function(l) {
                return l.serialize();
            });
            var maskOpts = _(this.outlineLayers).map(function(l) {
                return l.serialize();
            });

            return {
                experiment: this.experiment.serialize(),
                selectionHandler: this.selectionHandler.serialize(),
                channelLayerOptions: channelOpts,
                maskLayerOptions: maskOpts,
                mapState: mapState
            };
        });

        return bpPromise;
    }
}
