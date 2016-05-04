interface ToolResultArgs {
    id: string;
    name: string;
    layer: LabelLayer;
    plots: Plot[];
    visible?: boolean;
}

class ToolResult {

    id: string;
    name: string;
    layer: LabelLayer;
    plots: Plot[];

    private _visible: boolean;
    private _viewer: Viewer = null;

    get visible() {
        return this._visible;
    }

    set visible(doShow: boolean) {
        this.layer.visible = doShow;
        this.plots.forEach((pl) => {
            pl.visible = doShow;
        });
        this._visible = doShow;
    }

    delete() {
        this._viewer.viewport.removeLayer(this.layer);
    }

    constructor(args: ToolResultArgs) {
        this.id = args.id;
        this.name = args.name;
        this.layer = args.layer;
        this.plots = args.plots;
        this.visible = args.visible !== undefined ? args.visible : false;
    }

    attachToViewer(viewer: Viewer) {
        this._viewer = viewer;
        this._viewer.viewport.addLayer(this.layer);
    }
}
