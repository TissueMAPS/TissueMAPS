interface SerializedChannel {
    id: string;
    name: string;
    layers: SerializedChannelLayer[];
}

/**
 * Channel constructor arguments.
 */
interface ChannelArgs extends SerializedChannel {
    visible?: boolean;
}

class Channel implements Layer {
    id: string;
    name: string;

    private _layers: {[z: number]: ChannelLayer;} = {};
    private _currentZplane = 0;
    private _visible: boolean;

    /**
     * Construct a new Channel.
     *
     * @class Channel
     * @classdesc A channel represents a collection of layers acquired at
     * different z levels. A channel is visualized as a single layer that can
     * be colorized. 
     * @param {ChannelArgs} args - An argument object of type ChannelArgs.
     * @param {string} args.id - The id of this channel that was given by the server.
     * @param {string} args.name - A descriptive name for this channel (displayed in the UI).
     * @param {Array.<ChannelLayer>} args.name - A descriptive name for this channel (displayed in the UI).
     * @param {boolean} args.visible - If the channel should be visible when it is added. Default is false.
     */
    constructor(args: ChannelArgs) {
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

        var isChannelVisible = args.visible !== undefined ? args.visible : true;
        args.layers.forEach((l) => {
            var isBottomLayer = l.zplane === 0;
            this._layers[l.zplane] = new ChannelLayer({
                id: l.id,
                tpoint: l.tpoint,
                zplane: l.zplane,
                maxZoom: l.max_zoom,
                imageSize: l.image_size,
                visible: isChannelVisible && isBottomLayer
            });
        });
        this._visible = isChannelVisible;
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
     * Specify the z plane that should be visualized. This will hide all other
     * layers that belong to this channel.
     * @param {number} z - The new currently active z plane.
     */
    setZplane(z: number) {
        if (z == this._currentZplane) {
            return;
        }
        var prevLayer = this._layers[this._currentZplane];
        var nextLayer = this._layers[z];
        if (this._visible && prevLayer !== undefined) {
            prevLayer.visible = false;
        }
        if (this._visible && nextLayer !== undefined) {
            nextLayer.visible = true;
        }
        this._currentZplane = z;
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
        var layer = this._layers[this._currentZplane];
        if (layer !== undefined) {
            layer.visible = val;
        }
        this._visible = val;
    }

    /**
     * @property {number} maxZ - The maximum z plane to which this channel can
     * be visualized. Setting the value above this value has to effect.
     */
    get maxZ(): number {
        return Math.max.apply(this, _.keys(this._layers));
    }

    /**
     * @property {number} minZ - The minimum z plane to which this channel can
     * be visualized. Setting the value below this value has to effect.
     * Normally this value is set to 0.
     * @default 50
     */
    get minZ(): number {
        return Math.min.apply(this, _.keys(this._layers));
    }
}
