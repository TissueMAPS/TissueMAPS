class PlotResult extends LayerResult {
    constructor(name: string, session: ToolSession) {
        super(name, session);
        this._layer = new VisualLayer(this.name, {
            visible: true,
            visuals: []
        });
    }
}
