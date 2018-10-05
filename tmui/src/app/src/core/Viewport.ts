// Copyright (C) 2016-2018 University of Zurich.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// FIXME: This belongs to the serialization process that 
// is currently not functional.
interface MapState {
    zoom: number;
    center: ol.Coordinate;
    resolution: number;
    rotation: number;
}


// FIXME: This belongs to the serialization process that 
// is currently not functional.
interface SerializedViewport extends Serialized<Viewport> {
    // TODO: Create separate interface for serialized layer options.
    // The color object on channelLayerOptions isn't a full Color object
    // when restored.
    channelLayerOptions: ImageTileLayerArgs[];
    mapState: MapState;
}


class ResetViewControl extends ol.control.Control {
    /**
     * Create a object of class ResetViewControl
     * @class ResetViewControl
     * @classdesc A control that resets the map view to the original position.
     */
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
    /**
     * The underlying openlayers map.
     * This object should not be accessed from outside this class.
     */
    map: ol.Map;

    /**
     * All layers currently visualized by this viewport.
     */
    layers: Layer[] = [];

    /**
     * Constructor for a viewport.
     * @class Viewport
     * @classdesc A viewport is basically a wrapper around an openlayers map object
     * and stores layer objects which themselves are ultimately wrappers of openlayers
     * layer objects.
     * Before a viewport object can be used the methods `renderMap` and `initMap`
     * have to be called.
     */
    constructor() {
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

    /**
     * Get the map size.
     * @returns {Size} The map size.
     */
    get mapSize(): Size {
        // [minx miny maxx maxy]
        var ext = this.map.getView().getProjection().getExtent();
        return {
            width: ext[2],
            height: ext[3]
        };
    }

    /**
     * Add a layer to this viewport.
     * @param {Layer} layer - The layed to be added.
     */
    addLayer(layer: Layer) {
        layer.addToMap(this.map);
        this.layers.push(layer);
    }

    /**
     * In order for the visualization to work correctly, the valid resolutions
     * (i.e. zoom levels) that can be viewed has to be computed based on the
     * final map size.
     * This method further sets the openlayers view and as such has to be called
     * before anything is displayed.
     * @param {Size} mapSize - The size that the map should have.
     * Nothing outside this area will be displayed.
     */
    initMap(mapSize: Size) {
        // Center the view in the iddle of the image
        // (Note the negative sign in front of half the height)
        var width = mapSize.width
        var height = mapSize.height;
        var center = [width / 2, - height / 2];
        var extent = [0, 0, width, height];

        // Calculate the maximal resolution from the image size.
        // This corresponds to max number of squared tiles in either the height
        // or width of the image.
        var maxRes = 1;
        var tileSizeIter = 256;
        while (width > tileSizeIter || height > tileSizeIter) {
            tileSizeIter *= 2;
            maxRes *= 2;
        }

        var view = new ol.View({
            projection: new ol.proj.Projection({
                code: 'tm',
                units: 'pixels',
                extent: extent
            }),
            resolution: maxRes,
            center: center,
            zoom: 0 // 0 is zoomed out all the way
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

    /**
     * Update the map size (useful when the browser window changed).
     */
    update() {
        this.map.updateSize();
    }

    /**
     * Move the focus to a given mapobject.
     * @param {MapObject} obj - The mapobject that should be brought in view.
     */
    goToMapObject(obj: MapObject) {
        console.log('TODO: Get outline polygon from server for the following mapobject:');
        // this.map.getView().fit(<ol.geom.SimpleGeometry> feat.getGeometry(), this.map.getSize(), {
        //     padding: [100, 100, 100, 100]
        // });
    }

    // FIXME: This belongs to the serialization process that 
    // is currently not functional.
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

    /**
     * Inject the openlayers map into the DOM.
     * This method should be called when the container element is ready
     * (e.g. inside a directive containing the viewport container: tmViewport)
     * @param {Element} element - Where the map should be injected.
     */
    renderMap(element: Element) {
        this.map.setTarget(element);
    }
}
