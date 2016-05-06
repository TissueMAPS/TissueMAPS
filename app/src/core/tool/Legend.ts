abstract class Legend {
    protected _element: JQuery;

    private _visible: boolean;

    constructor(element: JQuery) {
        this._element = $('<div class="legend"></div>').append(element);
    }

    set visible(doShow: boolean) {
        if (doShow) {
            this._element.show();
        } else {
            this._element.hide();
        }
        this._visible = doShow;
    }

    attachToViewer(viewer: Viewer) {
        var legendContainer = viewer.element.find('.legends');
        legendContainer.append(this._element);
    }

    delete() {
        this._element.remove();
    }
}

class NullLegend extends Legend {
    constructor() {
        super($('<div></div>'));
    }
}
