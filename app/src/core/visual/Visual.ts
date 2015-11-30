interface Visualizable {
    getVisual(): Visual;
}

abstract class Visual {

    private _olFeature: ol.Feature;

    get olFeature() {
        return this._olFeature;
    }

    constructor(olFeature: ol.Feature) {
        this._olFeature = olFeature;
    }

//     get fillColor(): Color {
//         // var st: ol.style.Style = this._olFeature.getStyle();
//         // return Color.fromOlColor(st.getFill());
//         return Color.RED;
//     }

//     set fillColor(c: Color) {
//         // var st: ol.style.Style = this._olFeature.getStyle();
//         // st.getFill().setColor(c.toOlColor());
//     }

//     get strokeColor(): Color {
//         return Color.RED;
//     }

//     set strokeColor(c: Color) {

//     }

}

interface StrokeVisual {
    strokeColor: Color;
}

interface FillVisual {
    fillColor: Color;
}
