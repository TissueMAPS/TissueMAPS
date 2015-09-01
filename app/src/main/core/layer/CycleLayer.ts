/// <reference path='TileLayer.ts'/>

class CycleLayer extends TileLayer {
    constructor(ol, opt: ITileLayerArgs) {
        super(ol, opt);
    }
}

class CycleLayerFactory {
    static $inject = ['openlayers']
    constructor(private ol) {}
    create(opt: ITileLayerArgs) {
        return new CycleLayer(this.ol, opt);
    }
}

angular.module('tmaps.core.layer').service('CycleLayerFactory', CycleLayerFactory);

