class VisualLayerSettingsCtrl {

    viewport: Viewport;
    contentType: string;
    contentTypeEnum: ContentType;

    static $inject = ['$scope'];

    constructor() {
        this.contentTypeEnum = stringToContentType(this.contentType);
    }

    /**
     * Filter the layers on the template level to avoid generating a new array
     * each time the getter is accessed. This will cause the digest loop
     * to repeat infinitely.
     */
    get layers(): VisualLayer[] {
        return this.viewport.visualLayers;
    }

    removeLayer(layer: VisualLayer) {
        this.viewport.removeVisualLayer(layer);
    }

}

angular.module('tmaps.ui').controller('VisualLayerSettingsCtrl', VisualLayerSettingsCtrl);
