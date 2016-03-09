class LabelResult extends ToolResult {

    id: number;

    handle(viewer) {
        var layer = new LabelResultLayer(this.name, {
            size: viewer.viewport.mapSize,
            visible: true,
            labelResultId: this.id,
            t: 0,
            zlevel: 0
        });
        return viewer.viewport.addLayer(layer);
    }

    constructor(name: string, session: ToolSession, opt: {id: number;}) {
        super(name, session);
        this.id = opt.id
    }
}
