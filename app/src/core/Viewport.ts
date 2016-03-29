interface MapState {
    zoom: number;
    center: ol.Coordinate;
    resolution: number;
    rotation: number;
}

interface SerializedViewport extends Serialized<Viewport> {
    // TODO: Create separate interface for serialized layer options.
    // The color object on channelLayerOptions isn't a full Color object
    // when restored.
    channelLayerOptions: ImageTileLayerArgs[];
    mapState: MapState;
}

interface ViewportElementScope extends ng.IScope {
    viewport: Viewport;
    // TODO: Set type to that of ViewportCtrl
    viewportCtrl: any;
    appInstance: AppInstance;
}

class ResetViewControl extends ol.control.Control {
    constructor(args?: any) {
        args = args || {};
        var button = document.createElement('button');
        button.innerHTML = '<i class="fa fa-bullseye"></i>';
        button.addEventListener('click', (ev) => {
            var map = this.getMap();
            var view = map.getView();
            var mapSize = map.getSize();
            var ext = map.getView().getProjection().getExtent();
            var width = ext[2];
            var height = ext[3];
            view.setCenter([width / 2, -height / 2]);
            view.setZoom(0);
        });
        var element = document.createElement('div');
        element.className = 'reset-view-control ol-unselectable ol-control';
        element.appendChild(button);
        super({
            element: element,
            target: args.target
        });
    }
}


class Viewport implements Serializable<Viewport> {

    map: ol.Map;

    layers: Layer[] = [];

    private _$q: ng.IQService;
    private _$rootScope: ng.IRootScopeService;

    constructor() {
        this._$q = $injector.get<ng.IQService>('$q');
        this._$rootScope = $injector.get<ng.IRootScopeService>('$rootScope');

        this.map = new ol.Map({
            layers: [],
            controls: ol.control.defaults().extend(<ol.control.Control[]>[
                new ol.control.OverviewMap({
                    collapsed: true
                }),
                new ResetViewControl()
                // new ol.control.ScaleLine(),
                // new ol.control.ZoomToExtent()
            ]),
            renderer: 'webgl',
            logo: false
        });

        window['map'] = this.map;
    }

    get mapSize(): Size {
        // [minx miny maxx maxy]
        var ext = this.map.getView().getProjection().getExtent();
        return {
            width: ext[2],
            height: ext[3]
        };
    }


    addLayer(layer: Layer) {
        layer.addToMap(this.map);
        this.layers.push(layer);
    }

    initMap(mapSize: Size) {
        // Center the view in the iddle of the image
        // (Note the negative sign in front of half the height)
        var width = mapSize.width
        var height = mapSize.height;
        var center = [width / 2, - height / 2];
        var extent = [0, 0, width, height];
        var view = new ol.View({
            // We create a custom (dummy) projection that is based on pixels
            projection: new ol.proj.Projection({
                code: 'tm',
                units: 'pixels',
                extent: extent
            }),
            center: center,
            zoom: 0, // 0 is zoomed out all the way
            // TODO: start such that whole map is in view

        });

        this.map.setView(view);
    }

    /**
     * Remove a channelLayer from the map.
     * Use this method whenever a layer should be removed since it also updates
     * the app instance's internal state.
     */
    removeLayer(layer: Layer) {
        layer.removeFromMap(this.map);
        var idx = this.layers.indexOf(layer);
        this.layers.splice(idx, 1);
    }

    update() {
        this.map.updateSize();
    }

    goToMapObject(obj: MapObject) {
        var feat = obj.getVisual().olFeature;
        this.map.getView().fit(<ol.geom.SimpleGeometry> feat.getGeometry(), this.map.getSize(), {
            padding: [100, 100, 100, 100]
        });
    }

    serialize() {
        return <any>{};
            // var v = map.getView();

            // var mapState = {
            //     zoom: v.getZoom(),
            //     center: v.getCenter(),
            //     resolution: v.getResolution(),
            //     rotation: v.getRotation()
            // };

            // var channelOptsPr = this._$q.all(_(this.channelLayers).map((l) => {
            //     return l.serialize();
            // }));
            // var bundledPromises: any = {
            //     channels: channelOptsPr,
            // };
            // return this._$q.all(bundledPromises).then((res: any) => {
            //     return {
            //         channelLayerOptions: res.channels,
            //         mapState: mapState
            //     };
            // });
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

    renderMap(element: Element) {
        this.map.setTarget(element);
    }
}
