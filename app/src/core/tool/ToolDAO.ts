interface SerializedTool {
    id: string;
    name: string;
    description: string;
    icon: string;
}

class ToolDAO extends HTTPDataAccessObject<Tool> {
    constructor() {
        super('/api/tools')
    }

    fromJSON(data: SerializedTool) {
        return new Tool({
            id: data.id,
            name: data.name,
            description: data.description,
            icon: data.icon
        });
    }
}
