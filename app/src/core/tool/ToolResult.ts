abstract class ToolResult {

    visible: boolean;

    abstract show(viewer: AppInstance);
    abstract hide(viewer: AppInstance);

    constructor(public name: string, public session: ToolSession) {}

    // TODO: Solve this via some registration mechanism.
    static createToolResult(session: ToolSession, result: ServerToolResponse) {
        var time = (new Date()).toLocaleTimeString();
        var resultName = session.tool.name + ' at ' + time;
        switch (result.result_type) {
            case 'ClassifierResult':
                return new ClassifierResult(resultName, session, result.payload);
            case 'HeatmapResult':
                return new HeatmapResult(resultName, session, result.payload);
            default:
                console.log('Can\'t handle result:', result);
                break;
        }
    }
};
