interface MapState {
    zoom: number;
    center: ol.Coordinate;
    resolution: number;
    rotation: number;
}

interface SerializedViewport extends Serialized<Viewport> {
    experiment: SerializedExperiment;
    selectionHandler: SerializedSelectionHandler;
    channelLayerOptions: TileLayerArgs[];
    mapState: MapState;
}

interface ViewportElementScope extends ng.IScope {
    viewport: Viewport;
    // TODO: Set type to that of ViewportCtrl
    viewportCtrl: any;
}

class Viewport implements Serializable<Viewport> {

    experiment: Experiment;
    element: ng.IPromise<JQuery>;
    elementScope: ng.IPromise<ng.IScope>;
    map: ng.IPromise<ol.Map>;

    channelLayers: ChannelLayer[] = [];
    objectLayers: ObjectLayer[] = [];

    selectionHandler: CellSelectionHandler;

    tools: ng.IPromise<Tool[]>;

    constructor(private createViewportService: CreateViewportService,
                private ol,
                private $q: ng.IQService,
                private cellSelectionHandlerFty: CellSelectionHandlerFactory,
                private channelLayerFactory: ChannelLayerFactory,
                private experimentFactory: ExperimentFactory,
                private $http: ng.IHttpService,
                private Cell,
                private objectLayerFactory: ObjectLayerFactory,
                private toolLoader: ToolLoader,

                experiment: Experiment) {

        this.experiment = experiment;

        var mapDef = this.$q.defer();
        this.map = mapDef.promise;

        var elementDef = this.$q.defer();
        this.element = elementDef.promise;
        var elementScopeDef = this.$q.defer();
        this.elementScope = elementScopeDef.promise;

        // Helper class to manage the differently marker selections
        this.selectionHandler = this.cellSelectionHandlerFty.create(this);

        createViewportService.createViewport(
            this, 'viewports', '/templates/main/viewport.html'
        ).then(function(ret) {
            elementDef.resolve(ret.element);
            elementScopeDef.resolve(ret.scope);
            mapDef.resolve(ret.map);
        });

        // Load tools
        this.tools = this.toolLoader.loadTools(this);


        // var createDemoRectangles = function(startx, starty) {
        //     var side = 100;
        //     var nRect = 100;
        //     var cells = [];
        //     for (var i = startx; i <  side * nRect + startx; i += side) {
        //         for (var j = starty; j < side * nRect + starty; j += side) {
        //             var coords = [[
        //                 [i, -j],
        //                 [i + side, -j],
        //                 [i + side, -j - side],
        //                 [i, -j - side],
        //                 [i, -j]
        //             ]];
        //             var c = new this.Cell('bla', {x: i, y: -j}, coords);
        //             cells.push(c);
        //         }
        //     }
        //     return cells;
        // }

        // var cellsA = createDemoRectangles(0, 0);
        // var cellsB = createDemoRectangles(10000, 0);

        // var objLayerA = this.objectLayerFactory.create('Cells A', {
        //     objects: cellsA,
        //     fillColor: 'rgba(0, 0, 255, 0.5)',
        //     strokeColor: 'rgba(0, 0, 255, 1)'
        // });
        // var objLayerB = this.objectLayerFactory.create('Cells B', {
        //     objects: cellsB,
        //     fillColor: 'rgba(255, 0, 0, 0.5)',
        //     strokeColor: 'rgba(255, 0, 0, 1)'
        // });

        // this.addObjectLayer(objLayerA);
        // this.addObjectLayer(objLayerB);

        this.experiment.cells.then((cells) => {
            var cellLayer = this.objectLayerFactory.create('Cells', {
                objects: cells,
                fillColor: 'rgba(255, 0, 0, 0)',
                strokeColor: 'rgba(255, 0, 0, 1)'
            });
            this.addObjectLayer(cellLayer);
        });
    }

    initialize() {
        var layerOpts = _(this.experiment.channels).map((ch) => {
            return {
                name: ch.name,
                imageSize: ch.imageSize,
                pyramidPath: ch.pyramidPath
            };
        });
        console.log(layerOpts);
        console.log(this.experiment);
        this.addChannelLayers(layerOpts);
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

    // TODO: Handle this via mapobjects.
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
            console.log('sdf');
            this.addChannelLayer(opt);
        });
    }

    addChannelLayer(opt) {
        var channelLayer = this.channelLayerFactory.create(opt);
        var alreadyHasLayers = this.channelLayers.length !== 0;

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
            channelLayer.addToMap(map);
        });
        this.channelLayers.push(channelLayer);
    }

    /**
     * Remove a channelLayer from the map.
     * Use this method whenever a layer should be removed since it also updates
     * the app instance's internal state.
     */
    removeChannelLayer(channelLayer: ChannelLayer) {
        this.map.then(function(map) {
            channelLayer.removeFromMap(map);
        });
        var idx = this.channelLayers.indexOf(channelLayer);
        this.channelLayers.splice(idx, 1);
    }

    /**
     * Clean up method when the instance is closed (e.g. by deleting the Tab).
     */
    destroy() {
        this.elementScope.then((scope) => {
            scope.$destroy();
            this.element.then((element) => {
                // Destroy the stuff that this instance created
                element.remove();
            });
        });
    }

    show() {
        this.element.then((element) => {
            element.show();
            this.map.then((map) => {
                map.updateSize();
            });
        });
    }

    hide() {
        this.element.then((element) => {
            element.hide();
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

            var channelOptsPr = this.$q.all(_(this.channelLayers).map(function(l) {
                return l.serialize();
            }));
            var experimentPr =  this.experiment.serialize();
            var selectionHandlerPr = this.selectionHandler.serialize();
            var bundledPromises: any = {
                channels: channelOptsPr,
                exp: experimentPr,
                selHandler: selectionHandlerPr
            };
            return this.$q.all(bundledPromises).then((res: any) => {
                return {
                    channelLayerOptions: res.channels,
                    mapState: mapState,
                    experiment: res.exp,
                    selectionHandler: res.selHandler
                };
            });
        });

        return bpPromise;
    }
}
