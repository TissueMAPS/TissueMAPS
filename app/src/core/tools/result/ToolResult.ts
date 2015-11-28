interface ToolResult {};

interface LayerToolResult extends ToolResult {
    asVisualLayer(): VisualLayer;
}

interface PrintableToolResult extends ToolResult {
    asString(): string;
}
