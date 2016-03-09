class ChannelSettingsCtrl {
    viewport: Viewport;

    static $inject = ['$scope'];

    private _cachedLayers: ChannelLayer[];

    constructor() {}

    get layers(): ChannelLayer[] {
        var layers = <ChannelLayer[]> _(this.viewport.layers).filter((l) => {
            return l instanceof ChannelLayer;
        });
        if (!this._cachedLayers
            || layers.length !== this._cachedLayers.length) {
            this._cachedLayers = layers;
        }
        return this._cachedLayers;
    }

}
angular.module('tmaps.ui').controller('ChannelSettingsCtrl', ChannelSettingsCtrl);
