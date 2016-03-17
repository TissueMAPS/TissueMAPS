abstract class ToolResult {

    visible: boolean;

    abstract show(viewer: AppInstance);
    abstract hide(viewer: AppInstance);

    constructor(public name: string, public session: ToolSession) {}

    static createToolResult(session: ToolSession, result: ServerToolResponse) {
        var time = (new Date()).toLocaleTimeString();
        var resultName = session.tool.name + ' at ' + time;
        switch (result.result_type) {
            case 'LabelResult':
                console.log('Received LabelResult:', result);
                return new LabelResult(resultName, session, result.payload);
            case 'SimpleResult':
                console.log('Received SimpleResult:', result);
                return undefined;
            default:
                console.log('Can\'t handle result:', result);
                break;
        }
    }
};
