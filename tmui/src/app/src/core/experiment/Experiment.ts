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
/**
 * Experiment constructor arguments.
 * NOTE: This is currently just the serialized experiment and thus
 * will have underscore-separated variable names
 */
type ExperimentArgs = SerializedExperiment;


class Experiment implements Model {
    id: string;
    name: string;
    description: string;

    private _$http: ng.IHttpService;
    private _$q: ng.IQService;

    /**
     * Construct a new Experiment.
     * @class Experiment
     * @classdesc An experiment is the main container for data acquired by a 
     * microscope. Most of the functionality of TissueMAPS is provided by
     * the experiment object together with an object of type Viewer.
     * An experiment should be more of a data container and the viewer should
     * have the active role in the application.
     * @param {ExperimentArgs} args - Constructor arguments.
     */
    constructor(args: ExperimentArgs) {

        this._$http = $injector.get<ng.IHttpService>('$http');
        this._$q = $injector.get<ng.IQService>('$q');

        this.id = args.id;
        this.name = args.name;
        this.description = args.description;

    }

    getChannels(): ng.IPromise<any> {
        // TODO: use ChannelDAO
        return this._$http.get('/api/experiments/' + this.id + '/channels')
        .then((resp: any) => {
            return resp.data.data.map((ch, index) => {
                return new Channel({
                    id: ch.id,
                    layers: ch.layers,
                    name: ch.name,
                    bitDepth: ch.bit_depth,
                    visible: index === 0
                });
            });
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    getMapobjectTypes(): ng.IPromise<any> {
        // TODO: use MapobjectTypeDAO
        return this._$http.get('/api/experiments/' + this.id + '/mapobject_types')
        .then((resp: any) => {
            // console.log(resp)
            // var mapobjectTypes = (resp.data.data);
            return resp.data.data.map((mt) => {
                return new MapobjectType(mt);
            });
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    getPlates(): ng.IPromise<any> {
        return (new PlateDAO(this.id)).getAll()
        .then((plates) => {
            // console.log(plates)
            return plates;
        })
        .catch((error) => {
            return this._$q.reject(error);
        });
    }

}
