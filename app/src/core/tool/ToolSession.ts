class ToolSession {

    uuid: string;
    tool: Tool;
    isRunning: boolean = false;
    results: ToolResult[] = [];

    constructor(tool: Tool) {
        this.tool = tool;
        this.uuid = makeUUID();
    }
}
