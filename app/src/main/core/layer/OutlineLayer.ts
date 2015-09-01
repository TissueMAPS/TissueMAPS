/// <reference path='TileLayer.ts'/>

class OutlineLayer extends TileLayer {
    constructor(ol, opt: ITileLayerArgs) {
        super(ol, opt);
    }
}

class OutlineLayerFactory {
    static $inject = ['openlayers']
    constructor(private ol) {}
    create(opt: ITileLayerArgs) {
        return new OutlineLayer(this.ol, opt);
    }
}

angular.module('tmaps.core.layer').service('OutlineLayerFactory', OutlineLayerFactory);

