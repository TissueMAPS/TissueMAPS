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
    legend: Legend;
    plots: Plot[];

    private _visible: boolean;
    private _viewer: Viewer = null;

    get visible() {
        return this._visible;
    }

    set visible(doShow: boolean) {
        if (this.layer) {
            this.layer.visible = doShow;
        }
        if (this.legend) {
            this.legend.visible = doShow;
        }
        this.plots.forEach((pl) => {
            pl.visible = doShow;
        });
        this._visible = doShow;
    }

    delete() {
        if (this.layer) {
            this._viewer.viewport.removeLayer(this.layer);
        }
        if (this.legend) {
            this.legend.delete();
        }
    }

    constructor(args: ToolResultArgs) {
        this.id = args.id;
        this.name = args.name;
        this.layer = args.layer !== undefined ? args.layer : null;
        if (this.layer) {
            this.legend = this.layer.getLegend();
        } else {
            this.legend = null;
        }
        this.plots = args.plots !== undefined ? args.plots : [];
        this.visible = args.visible !== undefined ? args.visible : false;
    }

    attachToViewer(viewer: Viewer) {
        this._viewer = viewer;
        if (this.layer) {
            this._viewer.viewport.addLayer(this.layer);
            this.legend.attachToViewer(viewer);
        }
    }
}
