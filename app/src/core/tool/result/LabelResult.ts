class LabelResult extends LayerResult {

    id: number;

    constructor(name: string, session: ToolSession,
                args: {id: number;}) {
        this.id = args.id;
        this.name = name;
        super(name, session);
    }

    show(viewer: AppInstance) {
        if (this._layer === undefined) {
            this._layer = new LabelResultLayer({
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
