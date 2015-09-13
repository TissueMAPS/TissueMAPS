interface ToolResult {};

interface LayerToolResult extends ToolResult {
    asObjectLayer(): ObjectLayer;
}

interface PrintableToolResult extends ToolResult {
    asString(): string;
}
