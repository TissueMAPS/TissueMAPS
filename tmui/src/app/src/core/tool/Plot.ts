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
