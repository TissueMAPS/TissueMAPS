abstract class ToolResult {

    name: string;
    session: ToolSession;

    abstract handle(viewer: AppInstance);

    constructor(name: string, session: ToolSession) {
        this.name = name;
        this.session = session;
    }
};
