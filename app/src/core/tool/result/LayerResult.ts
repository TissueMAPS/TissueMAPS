abstract class LayerResult extends ToolResult implements Layer {
    protected _layer: VisualTileLayer;

    get opacity() {
        return this._layer.opacity;
    }

    set opacity(v: number) {
        this._layer.opacity = v;
    }

    get visible() {
        return this._layer.visible;
    }

    set visible(val: boolean) {
        this._layer.visible = val;
    }

    addToMap(map: ol.Map) {
        this._layer.addToMap(map);
    }
    
    removeFromMap(map: ol.Map) {
        this._layer.removeFromMap(map);
    }

    show(viewer: AppInstance) {
        this._layer.visible = true;
    }
    
    hide(viewer: AppInstance) {
        this._layer.visible = false;
    }
}
