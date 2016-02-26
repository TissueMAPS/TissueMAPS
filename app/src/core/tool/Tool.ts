interface ServerToolResponse {
    tool_id: string;
    result: any;
}

abstract class Tool {
    sessions: ToolSession[];
    results: ToolResult[];

    constructor(public appInstance: AppInstance,
                public id: string,
                public name: string,
                public description: string,
                public templateUrl: string,
                public icon: string,
                public defaultWindowHeight: number,
                public defaultWindowWidth: number) {
        this.sessions = [];
        this.results = [];
    }

    abstract handleResult(res: ToolResult);

    createSession() {

    }
    // createNewWindow() {
    //     var windowObj = this._openWindow();
    //     var toolWindow = {
    //         windowObject: windowObj
    //     };
    //     this.windows.push(toolWindow);

    //     $injector.get<JQueryStatic>('$')(windowObj).bind('beforeunload', (event) => {
    //         var idx = this.windows.indexOf(toolWindow);
    //         this.windows.splice(idx, 1);
    //     });

    //     return toolWindow;
    // }

    sendRequest(payload: any): ng.IPromise<ToolResult> {
        var url = '/api/tools/' + this.id + '/request';

        this.appInstance.viewport.elementScope.then((vpScope) => {
            vpScope.$broadcast('toolRequestSent');
        });

        return $injector.get<ng.IHttpService>('$http').post(url, {
            'experiment_id': this.appInstance.experiment.id,
            'payload': payload
        }).then(
        (resp) => {
            this.appInstance.viewport.elementScope.then((vpScope) => {
                vpScope.$broadcast('toolRequestDone');
                vpScope.$broadcast('toolRequestSuccess');
            });
            var data = <ServerToolResponse> resp.data;
            this.results.push(data.result);
            this.handleResult(data.result);
            return data.result;
        },
        (err) => {
            this.appInstance.viewport.elementScope.then((vpScope) => {
                vpScope.$broadcast('toolRequestDone');
                vpScope.$broadcast('toolRequestFailed', err.data);
            });
            return err.data;
        });
    };
}
