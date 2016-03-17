interface SerializedChannel {
    id: string;
    name: string;
    layers: SerializedChannelLayer[];
}

interface ChannelArgs extends SerializedChannel {
    visible?: boolean;
}

class Channel implements Layer {
    id: string;
    name: string;

    private _layers: {[z: number]: ChannelLayer;} = {};
    private _currentZplane = 0;
    private _visible: boolean;

    constructor(args: ChannelArgs) {
        this.name = args.name;
        this.id = args.id;
        args.layers.forEach((l) => {
            this._layers[l.zplane] = new ChannelLayer(l);
        });
        this.visible = args.visible;
    }

    get layers() {
        return _.values(this._layers);
    }

    addToMap(map: ol.Map) {
        _.values(this._layers).forEach((l) => {
            l.addToMap(map);
        });
    }

    removeFromMap(map: ol.Map) {
        _.values(this._layers).forEach((l) => {
            l.removeFromMap(map);
        });
    }

    setZplane(z: number) {
        console.log('channel: ', z);
        if (z == this._currentZplane) {
            return;
        }
        var prevLayer = this._layers[this._currentZplane];
        var nextLayer = this._layers[z];
        if (prevLayer !== undefined) {
            prevLayer.visible = false;
        }
        if (nextLayer !== undefined) {
            nextLayer.visible = true;
        }
        this._currentZplane = z;
    }

    get color(): Color {
        return _.values(this._layers)[0].color;
    }

    set color(val: Color) {
        _.values(this._layers).forEach((l) => {
            l.color = val;
        });
    }

    get min(): number {
        return _.values(this._layers)[0].min;
    }

    set min(val: number) {
        _.values(this._layers).forEach((l) => {
            l.min = val;
        });
    }

    get max(): number {
        return _.values(this._layers)[0].max;
    }

    set max(val: number) {
        _.values(this._layers).forEach((l) => {
            l.max = val;
        });
    }

    get brightness(): number {
        return _.values(this._layers)[0].brightness;
    }

    set brightness(val: number) {
        _.values(this._layers).forEach((l) => {
            l.brightness = val;
        });
    }

    get opacity(): number {
        return _.values(this._layers)[0].opacity;
    }

    set opacity(val: number) {
        _.values(this._layers).forEach((l) => {
            l.opacity = val;
        });
    }

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

    get maxZ(): number {
        return Math.max.apply(this, _.keys(this._layers));
    }

    get minZ(): number {
        return Math.min.apply(this, _.keys(this._layers));
    }
}
