class Layer {
    olLayer: ol.layer.Layer;

    constructor(public name: string) {}

    visible(val?: boolean): boolean {
        if (val !== undefined) {
            this.olLayer.setVisible(val);
            return val;
        } else {
            return this.olLayer.getVisible();
        }
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

