class LabelResult extends LayerResult {

    id: number;

    constructor(name: string, session: ToolSession,
                args: {id: number;}) {

        super(name, session);

        this.id = args.id;
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
