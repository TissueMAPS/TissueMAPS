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
interface Model {
    id: string;
}

interface APIError {
    status_code: number;
    message: string;
    // TODO: Include description for more detailed error report
}

abstract class HTTPDataAccessObject<T extends Model> {

    url: string;

    private _$http: ng.IHttpService;
    private _$q: ng.IQService;

    constructor(url: string) {
        this.url = url;
        this._$http = $injector.get<ng.IHttpService>('$http');
        this._$q = $injector.get<ng.IQService>('$q');
    }

    abstract fromJSON(json: any): T;

    /**
     * Query the server for a single specific model object.
     * someDAO.get(1).then((obj) => { .... });
     * @param {number} id - The id of the object to be fetched.
     * @returns {ng.IPromise<T[} | APIError>} Either a an object wrapped
     *          in a promise or an object of type APIError.
     */
    get(id: number): ng.IPromise<T | APIError> {
        return this._$http.get(this.url + '/' + id)
        .then((resp: any) => {
            return this.fromJSON(resp.data.data);
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    /**
     * Query the server for a list of model objects that satisfy a number
     * of constraints. Example:
     * someDAO.getAll({ parent_id: 2 }).then((objs) => { .... });
     * @param {Object} params - A map of query parameters.
     * @returns {ng.IPromise<T[} | APIError>} Either a list of objects wrapped
     *          in a promise or an object of type APIError.
     */
    getAll(params?: any): ng.IPromise<T[] | APIError> {
        var queryUrl;
        if (params === undefined || _.isEmpty(params)) {
            queryUrl = this.url;
        } else {
            var queryString = _.chain(params).pairs().map((arr) => {
                return arr[0] + '=' + arr[1];
            }).reduce((a, b) => {
                return a + '&' + b;
            }).value();
            queryUrl = this.url + '?' + queryString;
        }
        return this._$http.get(queryUrl)
        .then((resp: any) => {
            var serializedModels = (resp.data.data);
            return serializedModels.map((m) => {
                return this.fromJSON(m);
            });
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    /**
     * Create a server-side object.
     * Example:
     * someDAO.create({name: 'some name', prop2: 'some other property'});
     * @param {Object} data - The body of the object to be created.
     * @returns {ng.IPromise<T | APIError>} Either a the created object wrapped
     *          in a promise or an object of type APIError.
     */
    create(data: any): ng.IPromise<T | APIError> {
        return this._$http.post(this.url, data)
        .then((resp: {data: any}) => {
            return this.fromJSON(resp.data.data);
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    /**
     * Delete a server-side object given its id.
     * @param {number} id - The id of the object to be deleted.
     * @returns {ng.IPromise<T | APIError>} Either boolean indicator flag wrapped
     *          in a promise or an object of type APIError.
     */
    delete(id: string): ng.IPromise<boolean | APIError> {
        return this._$http.delete(this.url + '/' + id)
        .then((resp) => {
            return true;
        })
        .catch((resp) => {
            return resp.data.error;
        });
    }

    /**
     * Update a server-side object given its id.
     * @param {number} id - The id of the object to be deleted.
     * @param {Object} props - A mapping of property names to their values.
     * @returns {ng.IPromise<T | APIError>} Either boolean indicator flag wrapped
     *          in a promise or an object of type APIError.
     */
    update(id: string, props: any): ng.IPromise<boolean | APIError> {
        return this._$http.put(this.url + '/' + id, props)
        .then((resp) => {
            return true;
        })
        .catch((resp) => {
            return resp.data.error;
        });
    }
}
