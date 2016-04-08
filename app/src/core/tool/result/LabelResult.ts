interface LabelColorMapper {
    (label: any): Color;
}

interface LabelResultPayload {
    id: number;
    attributes: any;
}

abstract class LabelResult extends LayerResult {

    id: number;
    attributes: any;

    abstract getLabelColorMapper(): LabelColorMapper;

    constructor(name: string, session: ToolSession, payload: LabelResultPayload) {

        super(name, session);

        this.id = payload.id;
        this.attributes = payload.attributes;
    }

    show(viewer: AppInstance) {
        if (this._layer === undefined) {
            this._layer = new LabelResultLayer({
                size: viewer.viewport.mapSize,
                visible: false,
                labelResultId: this.id,
                t: 0,
                zlevel: 0,
                labelColorMapper: this.getLabelColorMapper()
            });
            viewer.viewport.addLayer(this._layer);
        }
        super.show(viewer);
    }
}
