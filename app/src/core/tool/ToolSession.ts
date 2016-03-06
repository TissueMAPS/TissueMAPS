abstract class ToolSession {

    uuid: string;
    tool: Tool;
    isRunning: boolean = false;
    results: ToolResult[] = [];

    constructor(tool: Tool) {
        this.tool = tool;
        this.uuid = makeUUID();
    }

    abstract handleResult(res: any);

    sendRequest(experiment: Experiment,
                payload: any): ng.IPromise<any> {
        var url = '/api/tools/' + this.tool.id + '/request';
        // TODO: Send event to Viewer messagebox
        return $injector.get<ng.IHttpService>('$http').post(url, {
            'experiment_id': experiment.id,
            'session_uuid': this.uuid,
            'payload': payload
        }).then(
        (resp) => {
            // TODO: Send event to Viewer messagebox
            // vpScope.$broadcast('toolRequestDone');
            // vpScope.$broadcast('toolRequestSuccess');
            var data = <ServerToolResponse> resp.data;
            var sessionUUID = data.session_uuid;
            var toolId = data.tool_id;
            var resultPayload = data.payload;
            this.results.push(resultPayload);
            this.handleResult(resultPayload);
            return data.payload;
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
