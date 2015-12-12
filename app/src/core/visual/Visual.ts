interface Visualizable {
    getVisual(): Visual;
}

abstract class Visual {
    protected _olFeature: ol.Feature;

    get olFeature() {
        return this._olFeature;
    }

    constructor(olFeature: ol.Feature) {
        this._olFeature = olFeature;
    }
}

class ColorizableVisual extends Visual {
    get strokeColor(): Color {
        var feat = this._olFeature;
        var st = <ol.style.Style> this._olFeature.getStyle();
        return Color.fromOlColor(st.getStroke().getColor());
    }

    set strokeColor(c: Color) {
        var st = <ol.style.Style> this._olFeature.getStyle();
        st.getStroke().setColor(c.toOlColor());
    }

    get fillColor(): Color {
        var st = <ol.style.Style> this._olFeature.getStyle();
        return Color.fromOlColor(<ol.Color> st.getFill().getColor());
    }

    set fillColor(c: Color) {
        var st = <ol.style.Style> this._olFeature.getStyle();
        st.getFill().setColor(c.toOlColor());
    }
}

interface ColorizableOpts {
    fillColor?: Color;
    strokeColor?: Color;
}

