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
interface SerializedAcquisition {
    id: string;
    name: string;
    description: string;
    status: string;
}

class AcquisitionDAO extends HTTPDataAccessObject<Acquisition> {

    /**
     * @classdesc A DataAccessObject for the Acquisition class.
     */
    constructor(experimentId: string) {
        super('/api/experiments/' + experimentId + '/acquisitions')
    }

    fromJSON(aq: SerializedAcquisition) {
        return new Acquisition({
            id: aq.id,
            name: aq.name,
            status: aq.status,
            description: aq.description
        });
    }
}
