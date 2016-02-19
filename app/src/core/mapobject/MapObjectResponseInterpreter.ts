class MapObjectResponseInterpreter {
    getObjectsForResponse(type: MapObjectType,
                          response: MapObjectTypeResponse): MapObject[] {
        switch (response.visual_type) {
            case 'polygon':
                return this._getForPolygonVisualType(type, response);
                break;
            default:
                throw new Error('Response has unknown visual type');
        }
    }

    private _getForPolygonVisualType(type: MapObjectType,
                                     response: MapObjectTypeResponse) {
        console.log(response);
        return _(response.ids).map((id) => {
            var coordinates = response.map_data.coordinates[id];
            var obj = new MapObject(id, type, 'polygon', {
                coordinates: coordinates !== undefined ? coordinates : []
            });
            return obj;
        });
    }
}
