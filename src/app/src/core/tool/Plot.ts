interface PlotArgs {
    id: string;
    attributes: string;
    visible?: boolean;
}

abstract class Plot {

    id: string;
    attributes: any;
    _visible: boolean;

    constructor(args: PlotArgs) {
        this.id = args.id;
        this.attributes = args.attributes;
        this.visible = args.visible !== undefined ? args.visible : false;
    }

    get visible() {
        return this._visible;
    }

    set visbile(v: boolean) {
        this._visible = v;
    }
}
