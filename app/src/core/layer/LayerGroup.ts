interface LayerGroupOpts {
    layers?: Layer[];
}

class LayerGroup implements Layer {
    name: string;
    private _layers: Layer[];

    constructor(name: string, opt?: LayerGroupOpts) {
        this.name = name;
        this._layers = opt.layers !== undefined ? opt.layers : [];
    }

    get visible() {
        return _(this._layers.map((l) => {
            return l.visible;
        })).every();
    }

    set visible(val: boolean) {
        this._layers.forEach((l) => {
            l.visible = val;
        });
    }

    addToMap(map: ol.Map) {
        this._layers.forEach((l) => {
            l.addToMap(map);
        });
    }
    
    removeFromMap(map: ol.Map) {
        this._layers.forEach((l) => {
            l.removeFromMap(map);
        });
    }

}
