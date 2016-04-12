/**
 * An interface for the content of the POST request that is sent to the 
 * server in order to perform a tool computation.
 * Such a request consists has to contain the id for the experiment for 
 * which the tool computation should be performed.
 * Furthermore, the tool session UUID has to be sent as well, so that the
 * server can provide the server-side tool session with session-specific
 * database storage.
 * Tool-specific data such as values for model parameters can be sent in the
 * payload object.
 */
interface ServerToolRequest {
    experiment_id: string;
    session_uuid: string;
    payload: any;
}

/**
 * An interface for the content of the AJAX response the server delivers
 * after processing a tool request.
 * The result_type will determine how the data contained in `payload` will
 * be processed client-side (e.g. visualized as a LabelResultLayer).
 */
interface ServerToolResponse {
    tool_id: number;
    session_uuid: any;
    result_type: string;
    payload: any;
}

/**
 * Interface for a serialized tool.
 * Objects adhering to this interface are sent 
 * as part of `GetToolsResponse`.
 */
interface GetToolResponse {
    id: string;
    name: string;
    description: string;
    icon: string;
}

interface GetToolsResponse {
    tools: GetToolResponse[];
}

/**
 * Argument object for constructing a tool.
 */
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

    /**
     * Construct a tool object.
     * @param {ToolArgs} args
     * @param {string} args.id - Tool id issued by the server.
     * @param {string} args.name - The name of the tool
     * that should be displayed in the UI.
     * @param {string} args.description - Helpful description of 
     * what this tool does.
     * @param {string} args.icon - 1-3 letter or symbol abbreviation
     * for this tool.
     */
    constructor(args: ToolArgs) {
        this.sessions = [];
        this.id = args.id;
        this.name = args.name;
        this.description = args.description;
        this.icon = args.icon;
    }

    /**
     * Get the controller that should be instantiated when
     * creating opening a window of this tool.
     * The tool creator has to make sure that
     * (1) this controller is named {tool.name}Ctrl, e.g. SVMToolCtrl, and
     * (2) that this file is compiled/executed s.t. this class is in the glboal
     * namespace.
     * @returns {ToolCtrl} An instance of a subclass of ToolCtrl.
     */
    get controller() {
        return window[this.name + 'Ctrl'];
    }

    /**
     * Get the url to the template for this tool.
     * This template is filled into the tool window container when clicking
     * on the tool button.
     * @returns {string}
     */
    get templateUrl() {
        return '/src/tools/' + this.name + '/' + this.name + 'Template.html';
    }

    /**
     * Create a new tool session and link it with this tool.
     * @todo Currently only 1 session is created per tool.
     * @returns ToolSession
     */
    createSession(): ToolSession {
        var sess = new ToolSession(this);
        this.sessions.push(sess);
        return sess;
    }

    /**
     * Get all tools for this user.
     * @todo Currently all tools are returned, regardless of which user
     * requested them.
     * @returns Promise.<Array.<Tool>>
     */
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
