interface ServerToolResponse {
    tool_id: number;
    session_uuid: any;
    payload: any;
}

abstract class ToolCtrl {

}

interface GetToolResponse {
    id: string;
    name: string;
    description: string;
    icon: string;
}

interface GetToolsResponse {
    tools: GetToolResponse[];
}

interface ToolArgs {
    id: string;
    name: string,
    description: string,
    icon: string,
}

class Tool {
    sessions: ToolSession[];
    id: string;
    name: string;
    description: string;
    icon: string;
    SessionClass: string;

    constructor(options: ToolArgs) {
        this.sessions = [];
        this.id = options.id;
        this.name = options.name;
        this.description = options.description;
        this.icon = options.icon;
    }

    get sessionClass() {
        return window[this.name + 'Session'];
    }

    get controller() {
        return window[this.name + 'Ctrl'];
    }

    get templateUrl() {
        return '/src/tools/' + this.name + '/' + this.name + 'Template.html';
    }

    createSession(): ToolSession {
        var sess = new this.sessionClass(this);
        this.sessions.push(sess);
        return sess;
    }


    static getAll(): ng.IPromise<Tool[]> {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.get('/api/tools').then((resp) => {
            var data = <GetToolsResponse> resp.data;
            return _.map(data.tools, (t) => {
                return new Tool({
                    id: t.id,
                    name: t.name,
                    description: t.description,
                    icon: t.icon
                });
            });
        });
    }

}
