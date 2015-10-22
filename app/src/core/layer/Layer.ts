interface Layer {
    name: string;
    addToMap(map: ol.Map);
    removeFromMap(map: ol.Map);
    visible: boolean;
}

class BaseLayer<LayerT extends ol.layer.Layer> implements Layer {
    protected olLayer: LayerT;

    constructor(public name: string) {}

    get visible(): boolean {
        return this.olLayer.getVisible();
    }

    set visible(val: boolean) {
        this.olLayer.setVisible(val);
    }

    /*
     * Draw the layer on the given openlayers map object
     */
    addToMap(olMap: ol.Map) {
        olMap.addLayer(this.olLayer);
    }

    /*
     * Remove the layer from the given openlayers map object
     */
    removeFromMap(olMap: ol.Map) {
        olMap.removeLayer(this.olLayer);
    }
}

