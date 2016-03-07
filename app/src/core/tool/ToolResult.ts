abstract class ToolResult {

    session: ToolSession;

    abstract handle(viewer: AppInstance);

    constructor(session: ToolSession) {
        this.session = session;
    }
};
