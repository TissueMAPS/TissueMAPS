// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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

