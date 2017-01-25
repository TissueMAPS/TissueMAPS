// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
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
/**
 * MapobjectType constructor arguments.
 */
interface SerializedMapobjectType {
    id: string;
    name: string;
    features: SerializedFeature[];
    layers: SerializedSegmentationLayer[];
}

interface MapobjectTypeArgs {
    id: string;
    name: string;
    features: SerializedFeature[];
    layers: SerializedSegmentationLayer[];
    visible?: boolean;
}


class MapobjectType implements Layer {
    id: string;
    name: string;
    features: Feature[];

    private _isStatic: boolean;
    private _layers: {[index: string]: SegmentationLayer;} = {};
    private _currentTpoint = 0;
    private _currentZplane = 0;
    private _visible: boolean;
    private _$stateParams: any;

    constructor(args: MapobjectTypeArgs) {
        this._$stateParams = $injector.get<any>('$stateParams');
        this.id = args.id;
        this.name = args.name;
        this.features = args.features;
        var isVisible = args.visible !== undefined ? args.visible : false;
        args.layers.forEach((l) => {
            var isBottomLayer = l.zplane === 0 && l.tpoint === 0;
            this._isStatic = l.zplane === null && l.tpoint === null;
            this._layers[l.tpoint + '-' + l.tpoint] = new SegmentationLayer({
                id: l.id,
                tpoint: l.tpoint,
                zplane: l.zplane,
                size: l.image_size,
                visible: isVisible && (isBottomLayer || this._isStatic)
            });
        })
        this._visible = isVisible;
    }

    /**
     * The layers that belong to this mapobject type
     * @name MapobjectType#layers
     * @type Array.<SegmentationLayer>
     * @default []
     */
    get layers() {
        return _.values(this._layers);
    }

    /**
     * Add the mapobject type to a map in order for it to be visualized.
     * @param {ol.Map} map - An openlayers map object.
     */
    addToMap(map: ol.Map) {
        _.values(this._layers).forEach((l) => {
            l.addToMap(map);
        });
    }

    /**
     * Remove the channel from the map making it no longer visible.
     * @param {ol.Map} map - An openlayers map object.
     */
    removeFromMap(map: ol.Map) {
        _.values(this._layers).forEach((l) => {
            l.removeFromMap(map);
        });
    }

    /**
     * Specify the plane that should be visualized. This will hide all other
     * layers that belong to this mapobject type.
     * @param {number} z - The new currently active z plane.
     * @param {number} t - The new currently active time point.
     */
    setPlane(z: number, t: number) {
        if (z == this._currentZplane && t == this._currentTpoint) {
            return;
        }
        var prevLayer = this._layers[this._currentZplane + '-' + this._currentTpoint];
        var nextLayer = this._layers[z + '-' + t];
        if (this._visible && prevLayer !== undefined) {
            prevLayer.visible = false;
        }
        if (this._visible && nextLayer !== undefined) {
            nextLayer.visible = true;
        }
        this._currentZplane = z;
        this._currentTpoint = t;
    }

    /**
     * @property {boolean} visible - If this mapobject type should be visible.
     * @default true
     */
    get visible(): boolean {
        return this._visible;
    }

    set visible(val: boolean) {
        if (this._isStatic) {
            var k = 'null-null';
        } else {
            var k = this._currentZplane + '-' + this._currentTpoint;
        }
        if (this._layers[k] !== undefined) {
            this._layers[k].visible = val;
        }
        this._visible = val;
    }

    private _getT(k: string) {
        var n = k.indexOf('-');
        return Number(k.substring(n+1));
    }

    private _getZ(k: string) {
        var n = k.indexOf('-');
        return Number(k.substring(0, n));
    }
    /**
     * @property {number} maxT - The maximum z plane to which this mapobject type can
     * be visualized. Setting the value above this value has to effect.
     */
    get maxT(): number {
        return Math.max.apply(this, _.keys(this._layers).map(this._getT));
    }

    /**
     * @property {number} minT - The minimum tim point plane to which this
     * mapobject type can be visualized. Setting the value below this value has to effect.
     * Normally this value is set to 0.
     * @default 0
     */
    get minT(): number {
        return Math.min.apply(this, _.keys(this._layers).map(this._getT));
    }

    /**
     * @property {number} maxZ - The maximum z plane to which this mapobject
     * type can be visualized. Setting the value above this value has to effect.
     */
    get maxZ(): number {
        return Math.max.apply(this, _.keys(this._layers).map(this._getZ));
    }

    /**
     * @property {number} minZ - The minimum z plane to which this mapobject
     * type be visualized. Setting the value below this value has to effect.
     * Normally this value is set to 0.
     * @default 0
     */
    get minZ(): number {
        return Math.min.apply(this, _.keys(this._layers).map(this._getZ));
    }
}
