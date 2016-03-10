class VisualLayerSettingsCtrl {

    viewport: Viewport;

    private _cachedLayers: VisualLayer[];

    constructor() {}

    /**
     * Filter the layers on the template level to avoid generating a new array
     * each time the getter is accessed. This will cause the digest loop
     * to repeat infinitely.
     */
    // get layers(): VisualLayer[] {
    //     var layers = <VisualLayer[]> _(this.viewport.layers).filter((l) => {
    //         return l instanceof LabelResultLayer;
    //     });
    //     if (!this._cachedLayers
    //         || layers.length !== this._cachedLayers.length) {
    //         this._cachedLayers = layers;
    //     }
    //     return this._cachedLayers;
    // }

    removeLayer(layer: VisualLayer) {
        this.viewport.removeLayer(layer);
    }

}

angular.module('tmaps.ui').controller('VisualLayerSettingsCtrl', VisualLayerSettingsCtrl);
