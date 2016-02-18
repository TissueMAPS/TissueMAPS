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

            // TODO: The coordinates are given in i/j format by the server and are recalculated here
            // to the x / -y format. This should be done on the server!
            if (coordinates !== undefined) {
                var ix;
                var nCoords = coordinates.length;
                for (ix = 0; ix < nCoords; ix++) {
                    var i = coordinates[ix][0];
                    var j = coordinates[ix][1];
                    coordinates[ix][0] = j; // x
                    coordinates[ix][1] = -i; // y
                }
            }

            var obj = new MapObject(id, type, 'polygon', {
                coordinates: coordinates !== undefined ? coordinates : []
            });
            return obj;
        });
    }
}
