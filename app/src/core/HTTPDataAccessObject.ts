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

    get(id: number): ng.IPromise<T | APIError> {
        return this._$http.get(this.url + '/' + id)
        .then((resp: any) => {
            return this.fromJSON(resp.data.data);
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    getAll(params?: any): ng.IPromise<T[] | APIError> {
        var queryUrl;
        if (params !== undefined) {
            var queryString = _.chain(params).pairs().map((arr) => {
                return arr[0] + '=' + arr[1];
            }).reduce((a, b) => {
                return a + '&' + b;
            }).value();
            queryUrl = this.url + '?' + queryString;
        } else {
            queryUrl = this.url;
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

    create(data: any): ng.IPromise<T | APIError> {
        return this._$http.post(this.url, data)
        .then((resp: {data: any}) => {
            return this.fromJSON(resp.data.data);
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    delete(id: string): ng.IPromise<boolean | APIError> {
        return this._$http.delete(this.url + id)
        .then((resp) => {
            return true;
        })
        .catch((resp) => {
            return resp.data.error;
        });
    }
}
