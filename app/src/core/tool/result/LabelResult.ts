class LabelResult extends ToolResult {
    id: number;

    handle(viewer) {
        console.log('TODO: ADD VISUALLAYER');
        var layer = new LabelResultLayer('new layer', {
            imageWidth: 15860,
            imageHeight: 9140, 
            visible: true,
            labelResultId: this.id,
            t: 0,
            zlevel: 0
        });
        return viewer.viewport.addVisualLayer(layer);
    }

    constructor(session: ToolSession, args: {id: number;}) {
        super(session);
        this.id = args.id
    }
}
