type ToolWindowId = string;

interface ServerToolResponse {
    tool_id: string;
    result: any;
}

interface ToolWindow {
    windowObject: Window
}

abstract class Tool {
    windows: ToolWindow[];
    results: ToolResult[];

    constructor(public appInstance: AppInstance,
                public id: string,
                public name: string,
                public description: string,
                public templateUrl: string,
                public icon: string,
                public defaultWindowHeight: number,
                public defaultWindowWidth: number) {
        this.windows = [];
        this.results = [];
    }

    abstract handleResult(result: ToolResult);

    getIdSlug(): string {
        return this.id.toLowerCase()
                      .replace(/[^A-Za-z0-9]+/g, '-')
                      .replace(/(^-|-$)/g, '');
    }

    createNewWindow() {
        var windowObj = this._openWindow();
        var toolWindow = {
            windowObject: windowObj
        };
        this.windows.push(toolWindow);

        $injector.get<JQueryStatic>('$')(windowObj).bind('beforeunload', (event) => {
            var idx = this.windows.indexOf(toolWindow);
            this.windows.splice(idx, 1);
        });

        return toolWindow;
    }

    private _openWindow() {
        // Without appending the current date to the title, the browser (chrome)
        // won't open multiple tool windows of the same type.
        var toolWindow = $injector.get<ng.IWindowService>('$window').open(
            '/src/toolwindow/', this.id, // + Date.now(),
            'toolbar=no,menubar=no,titebar=no,location=no,directories=no,replace=no,' +
            'width=' + this.defaultWindowWidth + ',height=' + this.defaultWindowHeight
        );

        if (_.isUndefined(toolWindow)) {
            throw new Error('Could not create tool window! Is your browser blocking popups?');
        }

        // Create a container object that includes ressources that the tool may
        // need.
        var init: ToolWindowInitObject = {
            appInstance: this.appInstance,
            viewportScope: this.appInstance.viewport.elementScope,
            applicationScope: $injector.get<ng.IRootScopeService>('$rootScope'),
            toolWindow: toolWindow,
            tool: this
        };

        // Save the initialization object to the local storage, such that the newly
        // created window may retrieve it.
        toolWindow.init = init;

        return toolWindow;
    }

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
