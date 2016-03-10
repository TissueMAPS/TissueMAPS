class LabelResult extends LayerResult {

    id: number;

    constructor(name: string, session: ToolSession,
                opt: {id: number;}) {
        this.id = opt.id;
        super(name, session);
    }

    show(viewer: AppInstance) {
        if (this._layer === undefined) {
            this._layer = new LabelResultLayer(this.name, {
                size: viewer.viewport.mapSize,
                visible: false,
                labelResultId: this.id,
                t: 0,
                zlevel: 0
            });
            viewer.viewport.addLayer(this._layer);
        }
        super.show(viewer);
    }
}
