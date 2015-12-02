class MapObjectResponseInterpreter {
    getObjectsForResponse(response: MapObjectTypeResponse): MapObject[] {
        switch (response.visual_type) {
            case 'polygon':
                return this._getForPolygonVisualType(response);
                break;
            default:
                throw new Error('Response has unknown visual type');
        }
    }

    private _getForPolygonVisualType(response: MapObjectTypeResponse) {
        return _(response.ids).map((id) => {
            return new MapObject(id, 'cell', 'polygon', {
                coordinates: response.map_data.coordinates[id]
            });
        });
    }
}
