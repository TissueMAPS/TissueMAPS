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
    session_uuid: string;
    tool_name: string;
    payload: any;
}

/**
 * An interface for the content of the AJAX response the server delivers
 * after processing a tool request.
 * The type of the result determines how the data contained in `payload` gets
 * handled client-side (e.g. visualized as a LabelLayer).
 */
interface ServerToolResponse {
    data: SerializedToolResult;
}

/**
 * Argument object for constructing a tool.
 */
interface ToolArgs {
    name: string,
    description: string,
    icon: string,
    methods: any[]
}

class Tool {
    sessions: ToolSession[];
    name: string;
    description: string;
    icon: string;
    methods: any[];

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
     * @param {[]} args.methods - Methods this tool supports
     */
    constructor(args: ToolArgs) {
        this.sessions = [];
        this.name = args.name;
        this.description = args.description;
        this.icon = args.icon;
        this.methods = args.methods;
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
}
