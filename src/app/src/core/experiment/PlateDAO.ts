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
interface SerializedPlate {
    id: string;
    name: string;
    description: string;
    acquisitions: SerializedAcquisition[];
    status: string;
}

class PlateDAO extends HTTPDataAccessObject<Plate> {

    experimentId: string;
    /**
     * @classdesc An DataAccessObject for querying and creating objects
     * of type Plate.
     */
    constructor(experimentId: string) {
        super('/api/experiments/' + experimentId + '/plates')
        this.experimentId = experimentId;
    }

    fromJSON(data: SerializedPlate) {
        return new Plate({
            id: data.id,
            name: data.name,
            description: data.description,
            acquisitions: data.acquisitions.map((acq) => {
                return (new AcquisitionDAO(this.experimentId)).fromJSON(acq);
            }),
            status: data.status
        });
    }
}
