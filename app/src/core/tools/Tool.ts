type ToolWindowId = string;

interface ServerToolResponse {
    tool_id: string;
    result: any;
}

interface ToolWindow {
    windowObject: Window
}

class Tool {
    windows: ToolWindow[];
    results: ToolResult[];

    private resultHandler: ToolResultHandler;

    constructor(protected $: JQueryStatic,
                protected $http: ng.IHttpService,
                protected $window: Window,
                protected $rootScope: ng.IRootScopeService,
                public appInstance: AppInstance,
                public id: string,
                public name: string,
                public description: string,
                public templateUrl: string,
                public icon: string,
                public defaultWindowHeight: number,
                public defaultWindowWidth: number,
                resultHandler: ToolResultHandler) {
        this.windows = [];
        this.results = [];
        this.resultHandler = resultHandler;
    }

    getIdSlug(): string {
        return this.id.toLowerCase()
                      .replace(/[^A-Za-z0-9]+/g, '-')
                      .replace(/(^-|-$)/g, '');
    }

    createNewWindow() {
        var windowObj = this.openWindow();
        var toolWindow = {
            windowObject: windowObj
        };
        this.windows.push(toolWindow);

        this.$(windowObj).bind('beforeunload', (event) => {
            var idx = this.windows.indexOf(toolWindow);
            this.windows.splice(idx, 1);
        });

        return toolWindow;
    }

    private openWindow() {
        // Without appending the current date to the title, the browser (chrome)
        // won't open multiple tool windows of the same type.
        var toolWindow = this.$window.open(
            '/src/toolwindow/', this.id, // + Date.now(),
            'toolbar=no,menubar=no,titebar=no,location=no,directories=no,replace=no,' +
            'width=' + this.defaultWindowWidth + ',height=' + this.defaultWindowHeight
        );

        if (_.isUndefined(toolWindow)) {
            throw new Error('Could not create tool window! Is your browser blocking popups?');
        }

        // Create a container object that includes ressources that the tool may
        // need.
        var init = {
            appInstance: this.appInstance,
            viewportScope: this.appInstance.viewport.elementScope,
            applicationScope: this.$rootScope,
            toolWindow: toolWindow,
            tool: this
        };

        // Save the initialization object to the local storage, such that the newly
        // created window may retrieve it.
        toolWindow.init = init;

        return toolWindow;
    }

    handleResult(result: ToolResult) {
        this.results.push(result);
        this.resultHandler.handle(result);
    }

    sendRequest(payload: any): ng.IPromise<ToolResult> {
        var url = '/api/tools/' + this.id + '/request';

        this.appInstance.viewport.elementScope.then((vpScope) => {
            vpScope.$broadcast('toolRequestSent');
        });

        return this.$http.post(url, {
            'payload': payload
        }).then(
        (resp) => {
            this.appInstance.viewport.elementScope.then((vpScope) => {
                vpScope.$broadcast('toolRequestDone');
                vpScope.$broadcast('toolRequestSuccess');
            });
            var data = <ServerToolResponse> resp.data;
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
