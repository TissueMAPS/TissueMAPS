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
interface SerializedChannel {
    id: string;
    name: string;
    bit_depth: number;
    layers: SerializedChannelLayer[];
}

/**
 * Channel constructor arguments.
 */
interface ChannelArgs {
    id: string;
    name: string;
    layers: SerializedChannelLayer[];
    bitDepth: number;
    visible?: boolean;
}

class Channel implements Layer {
    id: string;
    name: string;
    bitDepth: number;
    maxIntensity: number;
    minIntensity: number;

    private _layers: {[index: string]: ChannelLayer;} = {};
    private _currentTpoint = 0;
    private _currentZplane = 0;
    private _visible: boolean;
    private _$stateParams: any;

    /**
     * Construct a new Channel.
     *
     * @class Channel
     * @classdesc A channel represents a collection of layers acquired at
     * different z levels and time points. A channel is visualized as a single
     * layer that can
     * be colorized.
     * @param {ChannelArgs} args - An argument object of type ChannelArgs.
     * @param {string} args.id - The id of this channel that was given by the server.
     * @param {string} args.name - A descriptive name for this channel (displayed in the UI).
     * @param {number} args.bitDepth - Number of bits used to indicate intensity in the orginal images.
     * @param {Array.<ChannelLayer>} args.layers - Array of layers of type ChannelLayer.
     * @param {boolean} args.visible - If the channel should be visible when it is added. Default is false.
     */
    constructor(args: ChannelArgs) {
        this._$stateParams = $injector.get<any>('$stateParams');
        /**
         * @property {string} name - The name of this channel.
         * @default Color.WHITE
         */
        this.name = args.name;
        /**
         * @property {string} id - The id of this channel that was given by the server.
         * @default Color.WHITE
         */
        this.id = args.id;
        this.bitDepth = args.bitDepth;
        var isVisible = args.visible !== undefined ? args.visible : true;
        args.layers.forEach((l) => {
            var isBottomLayer = l.zplane === 0 && l.tpoint === 0;
            this._layers[l.zplane + '-' + l.tpoint] = new ChannelLayer({
                id: l.id,
                tpoint: l.tpoint,
                zplane: l.zplane,
                maxZoom: l.max_zoom,
                maxIntensity: l.max_intensity,
                minIntensity: l.min_intensity,
                imageSize: l.image_size,
                visible: isVisible && isBottomLayer
            });
        });
        this._visible = isVisible;
        if (_.values(this._layers).length > 0) {
            this.maxIntensity = _.values(this._layers)[0].maxIntensity;
            this.minIntensity = _.values(this._layers)[0].minIntensity;
        } else {
            this.minIntensity = 0;
            this.maxIntensity = 255;
        }
    }

    /**
     * The layers that belong to this channel
     * @name Channel#layers
     * @type Array.<ChannelLayer>
     * @default []
     */
    get layers() {
        return _.values(this._layers);
    }

    /**
     * Add the channel to a map in order for it to be visualized.
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
     * layers that belong to this channel.
     * @param {number} z - The new currently active z plane.
     * @param {number} t - The new currently active time point.
     */
    setPlane(z: number, t: number) {
        if (z == this._currentZplane && t == this._currentTpoint) {
            return;
        }
        // TODO: Preload tiles for other z-resolutions or time points
        // if (update == 'z') {
        //     for (var key in this._layers) {
        //         var currentZ = this._getZ(key);
        //         this._layers[currentZ + '-' + t].preload = true;
        //     }
        // } else {
        //     for (var key in this._layers) {
        //         var currentT = this._getT(key);
        //         this._layers[z + '-' + currentT].preload = true;
        //     }
        // }
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
     * @property {Color} color - The color with which this channel is to be multiplied.
     * @default Color.WHITE
     */
    get color(): Color {
        return _.values(this._layers)[0].color;
    }

    set color(val: Color) {
        _.values(this._layers).forEach((l) => {
            l.color = val;
        });
    }

    /**
     * @property {number} min - The lower bound used when stretching intensity
     * according to the formula I' = (I - min) / (max - min) * 255.
     * @default 0
     */
    get min(): number {
        return _.values(this._layers)[0].min;
    }

    set min(val: number) {
        _.values(this._layers).forEach((l) => {
            l.min = val;
        });
    }

    /**
     * @property {number} max - The upper bound used when stretching intensity
     * according to the formula I' = (I - min) / (max - min) * 255.
     * @default 255
     */
    get max(): number {
        return _.values(this._layers)[0].max;
    }

    set max(val: number) {
        _.values(this._layers).forEach((l) => {
            l.max = val;
        });
    }

    /**
     * @property {number} brightness - The brightness of the layers belonging to this channel.
     * @default 50
     */
    get brightness(): number {
        return _.values(this._layers)[0].brightness;
    }

    set brightness(val: number) {
        _.values(this._layers).forEach((l) => {
            l.brightness = val;
        });
    }

    /**
     * @property {number} opacity - The opacity of the layers belonging to this
     * channel. Ranges from 0 to 1.
     */
    get opacity(): number {
        return _.values(this._layers)[0].opacity;
    }

    set opacity(val: number) {
        _.values(this._layers).forEach((l) => {
            l.opacity = val;
        });
    }

    /**
     * @property {boolean} visible - If this channel should be visible.
     * @default true
     */
    get visible(): boolean {
        return this._visible;
    }

    set visible(val: boolean) {
        var k = this._currentZplane + '-' + this._currentTpoint;
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
     * @property {number} maxT - The maximum z plane to which this channel can
     * be visualized. Setting the value above this value has to effect.
     */
    get maxT(): number {
        return Math.max.apply(this, _.keys(this._layers).map(this._getT));
    }

    /**
     * @property {number} minT - The minimum tim point plane to which this
     * channel can be visualized. Setting the value below this value has to effect.
     * Normally this value is set to 0.
     * @default 50
     */
    get minT(): number {
        return Math.min.apply(this, _.keys(this._layers).map(this._getT));
    }

    /**
     * @property {number} maxZ - The maximum z plane to which this channel can
     * be visualized. Setting the value above this value has to effect.
     */
    get maxZ(): number {
        return Math.max.apply(this, _.keys(this._layers).map(this._getZ));
    }

    /**
     * @property {number} minZ - The minimum z plane to which this channel can
     * be visualized. Setting the value below this value has to effect.
     * Normally this value is set to 0.
     * @default 50
     */
    get minZ(): number {
        return Math.min.apply(this, _.keys(this._layers).map(this._getZ));
    }
}
