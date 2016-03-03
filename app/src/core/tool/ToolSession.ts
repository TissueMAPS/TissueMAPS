class ToolSession {

    id: string;
    tool: Tool;
    isRunning: boolean = false;
    results: ToolResult[] = [];

    constructor(tool: Tool) {
        this.tool = tool;
        this.id = makeUUID();
    }
}
