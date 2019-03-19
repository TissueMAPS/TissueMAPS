// Copyright (C) 2016-2018 University of Zurich.
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
abstract class Legend {
    protected _element: JQuery;

    private _visible: boolean;

    /**
     * @class Legend
     * @classdesc A legend that explains how a labellayer has to be
     * interpreted.
     * @param {JQuery} element - The element that represents this
     * legend. This element will be inserted into the DOM at the right place.
     */
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
    /**
     * @classdesc A dummy legend that does nothing.
     */
    constructor() {
        super($('<div></div>'));
    }
}
