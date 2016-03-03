interface ToolWindowOptions {
    templateUrl: string;
    icon: string;
    defaultWindowHeight: number;
    defaultWindowWidth: number;
}

interface ServerToolResponse {
    tool_id: string;
    result: any;
}

abstract class Tool {
    sessions: ToolSession[];

    constructor(public appInstance: AppInstance,
                public id: string,
                public name: string,
                public description: string,
                public windowOptions: ToolWindowOptions) {
        this.sessions = [];
    }

    abstract handleResult(res: ToolResult);

    createSession(): ToolSession {
        var sess = new ToolSession(this);
        this.sessions.push(sess);
        return sess;
    }

    sendRequest(session: ToolSession, payload: any): ng.IPromise<ToolResult> {
        var url = '/api/tools/' + this.id + '/request';

        // TODO: Send event to Viewer messagebox
        // this.appInstance.viewport.elementScope.then((vpScope) => {
        //     vpScope.$broadcast('toolRequestSent');
        // });

        return $injector.get<ng.IHttpService>('$http').post(url, {
            'experiment_id': this.appInstance.experiment.id,
            'payload': payload
        }).then(
        (resp) => {
            // this.appInstance.viewport.elementScope.then((vpScope) => {
                // TODO: Send event to Viewer messagebox
                // vpScope.$broadcast('toolRequestDone');
                // vpScope.$broadcast('toolRequestSuccess');
            // });
            var data = <ServerToolResponse> resp.data;
            session.results.push(data.result);
            this.handleResult(data.result);
            return data.result;
        },
        (err) => {
            // this.appInstance.viewport.elementScope.then((vpScope) => {
                // TODO: Send event to Viewer messagebox
                // vpScope.$broadcast('toolRequestDone');
                // vpScope.$broadcast('toolRequestFailed', err.data);
            // });
            return err.data;
        });
    };

}
