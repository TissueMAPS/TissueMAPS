class ObjectSettingsCtrl {

    viewport: Viewport;

    private _cachedLayers: SegmentationLayer[];

    constructor() {}

    get layers(): SegmentationLayer[] {
        var layers = <SegmentationLayer[]> _(this.viewport.layers).filter((l) => {
            return l instanceof SegmentationLayer;
        });
        if (!this._cachedLayers
            || layers.length !== this._cachedLayers.length) {
            this._cachedLayers = layers;
        }
        return this._cachedLayers;
    }

    removeLayer = function(layer) {
        this.viewport.removeLayer(layer);
    }

}

angular.module('tmaps.ui')
.controller('ObjectSettingsCtrl', ObjectSettingsCtrl);
