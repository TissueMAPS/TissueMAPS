interface MapState {
    zoom: number;
    center: ol.Coordinate;
    resolution: number;
    rotation: number;
}

interface SerializedViewport extends Serialized<Viewport> {
    selectionHandler: SerializedSelectionHandler;
    // TODO: Create separate interface for serialized layer options.
    // The color object on channelLayerOptions isn't a full Color object
    // when restored.
    channelLayerOptions: TileLayerArgs[];
    mapState: MapState;
}

interface ViewportElementScope extends ng.IScope {
    viewport: Viewport;
    // TODO: Set type to that of ViewportCtrl
    viewportCtrl: any;
    appInstance: AppInstance;
}

class Viewport implements Serializable<Viewport> {

    element: ng.IPromise<JQuery>;
    elementScope: ng.IPromise<ViewportElementScope>;
    map: ng.IPromise<ol.Map>;

    channelLayers: ChannelLayer[] = [];
    visualLayers: VisualLayer[] = [];

    selectionHandler: MapObjectSelectionHandler;

    private _mapDef: ng.IDeferred<ol.Map>;
    private _elementDef: ng.IDeferred<JQuery>;
    private _elementScopeDef: ng.IDeferred<ViewportElementScope>;

    private _$q: ng.IQService;
    private _$rootScope: ng.IRootScopeService;

    constructor() {

        this._$q = $injector.get<ng.IQService>('$q');
        this._$rootScope = $injector.get<ng.IRootScopeService>('$rootScope');

        this._mapDef = this._$q.defer();
        this.map = this._mapDef.promise;

        this._elementDef = this._$q.defer();
        this.element = this._elementDef.promise;

        this._elementScopeDef = this._$q.defer();
        this.elementScope = this._elementScopeDef.promise;

        // Helper class to manage the differently marker selections
        // TODO: dsf
        this.selectionHandler = new MapObjectSelectionHandler(this, ['cell']);

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

    }

    setSelectionHandler(sh: MapObjectSelectionHandler) {
        this.selectionHandler = sh;
    }

    addVisualLayer(visLayer: VisualLayer) {
        this.visualLayers.push(visLayer);
        this.map.then((map) => {
            visLayer.addToMap(map);
        });
    }

    removeVisualLayer(visLayer: VisualLayer) {
        var idx = this.visualLayers.indexOf(visLayer)
        if (idx !== -1) {
            this.map.then((map) => {
                visLayer.removeFromMap(map);
                this.visualLayers.splice(idx, 1);
            });
        }
    }

    addChannelLayer(channelLayer: ChannelLayer) {
        var alreadyHasLayers = this.channelLayers.length !== 0;

        // If this is the first time a layer is added, create a view and add it to the map.
        if (!alreadyHasLayers) {
            // Center the view in the iddle of the image
            // (Note the negative sign in front of half the height)
            var width = channelLayer.imageSize[0];
            var height = channelLayer.imageSize[1];
            var center = [width / 2, - height / 2];
            var view = new ol.View({
                // We create a custom (dummy) projection that is based on pixels
                projection: new ol.proj.Projection({
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

    goToMapObject(obj: MapObject) {
        this.map.then((map) => {
            var feat = obj.getVisual().olFeature;
            map.getView().fit(<ol.geom.SimpleGeometry> feat.getGeometry(), map.getSize(), {
                padding: [100, 100, 100, 100]
            });
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

            var channelOptsPr = this._$q.all(_(this.channelLayers).map((l) => {
                return l.serialize();
            }));
            var selectionHandlerPr = this.selectionHandler.serialize();
            var bundledPromises: any = {
                channels: channelOptsPr,
                selHandler: selectionHandlerPr
            };
            return this._$q.all(bundledPromises).then((res: any) => {
                return {
                    channelLayerOptions: res.channels,
                    mapState: mapState,
                    selectionHandler: res.selHandler
                };
            });
        });

        return bpPromise;
    }

    private getTemplate(templateUrl): ng.IPromise<string> {
        var deferred = this._$q.defer();
        $injector.get<ng.IHttpService>('$http')({method: 'GET', url: templateUrl, cache: true})
        .then(function(result) {
            deferred.resolve(result.data);
        })
        .catch(function(error) {
            deferred.reject(error);
        });
        return deferred.promise;
    }

    injectIntoDocumentAndAttach(appInstance: AppInstance) {
        this.getTemplate('/templates/main/viewport.html').then((template) => {
            var newScope = <ViewportElementScope> this._$rootScope.$new();
            newScope.viewport = this;
            newScope.appInstance = appInstance;
            var ctrl = $injector.get<any>('$controller')('ViewportCtrl', {
                '$scope': newScope,
                'viewport': this
            });
            newScope.viewportCtrl = ctrl;

            // The divs have to be shown and hidden manually since ngShow
            // doesn't quite work correctly when doing it this way.
            var elem = angular.element(template);

            // Compile the element (expand directives)
            var linkFunc = $injector.get<ng.ICompileService>('$compile')(elem);
            // Link to scope
            var viewportElem = linkFunc(newScope);

            // Append to viewports
            $injector.get<ng.IDocumentService>('$document').find('#viewports').append(viewportElem);
            // Append map after the element has been added to the DOM.
            // Otherwise the viewport size calculation of openlayers gets
            // messed up.
            var map = new ol.Map({
                layers: [],
                controls: [],
                renderer: 'webgl',
                target: viewportElem.find('.map-container')[0],
                logo: false
            });
            this._elementDef.resolve(viewportElem);
            this._elementScopeDef.resolve(newScope);
            this._mapDef.resolve(map);
        });
    }
}
