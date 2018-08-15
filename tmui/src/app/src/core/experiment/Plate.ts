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
interface PlateArgs {
    id: string;
    name: string;
    description: string;
    acquisitions: Acquisition[];
    status: string;
}

class Plate {
    id: string;
    name: string;
    description: string;
    status: string;
    acquisitions: Acquisition[];

    /**
     * Constructor a new Plate object.
     *
     * @class Plate
     * @classdesc A plate is basically a container for multiple objects
     * of type Acquisition.
     * @param {PlateArgs} args - Constructor arguments.
     */
    constructor(args: PlateArgs) {
        this.id = args.id;
        this.name = args.name;
        this.description = args.description;
        this.acquisitions = args.acquisitions;
        this.status = args.status;
    }

    get isReadyForProcessing() {
        var hasMinOneAcquisition = this.acquisitions.length > 0;
        var allAcquisitionsReady = _.all(this.acquisitions.map((aq) => {
            return aq.status === 'COMPLETE';
        }));
        return hasMinOneAcquisition && allAcquisitionsReady;
    }
}
