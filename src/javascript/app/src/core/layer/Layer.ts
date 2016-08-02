/**
 * Everything that can be added and removed to the viewport.
 */
interface Layer {
    addToMap(map: ol.Map);
    removeFromMap(map: ol.Map);
    visible: boolean;
}

/**
 * A class that wraps a openlayers layer.
 */
class BaseLayer<LayerT extends ol.layer.Layer> implements Layer {
    protected _olLayer: LayerT;

    get visible(): boolean {
        return this._olLayer.getVisible();
    }

    set visible(val: boolean) {
        this._olLayer.setVisible(val);
    }

    get opacity(): number {
        return this._olLayer.getOpacity();
    }

    set opacity(val: number) {
        this._olLayer.setOpacity(val);
    }

    /*
     * Draw the layer on the given openlayers map object
     *
     * Adding layer on top of all other layers is achieved by leaving the position
     * argument undefined. If the requested position is 0, the layer will
     * be added at the bottom.
     */
    addToMap(olMap: ol.Map, position?: number) {
        // olMap.addLayer(this._olLayer);
        var coll = olMap.getLayerGroup().getLayers();
        if (position !== undefined) {
            coll.insertAt(position, this._olLayer)
        } else {
            coll.push(this._olLayer);
        }
    }

    /*
     * Remove the layer from the given openlayers map object
     */
    removeFromMap(olMap: ol.Map) {
        olMap.removeLayer(this._olLayer);
    }
}

