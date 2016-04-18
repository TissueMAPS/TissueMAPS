abstract class ToolResult {

    visible: boolean;

    abstract show(viewer: Viewer);
    abstract hide(viewer: Viewer);

    constructor(public name: string, public session: ToolSession) {}

    static createToolResult(session: ToolSession, result: ServerToolResponse) {
        var time = (new Date()).toLocaleTimeString();
        var resultName = session.tool.name + ' at ' + time;
        var resultCls = window[result.result_type];
        if (resultCls !== undefined) {
            return new resultCls(resultName, session, result.payload);
        } else {
            throw new Error(
                'No client-side result class found that can handle results of class: ' +
                result.result_type
            );
        }
    }
};
