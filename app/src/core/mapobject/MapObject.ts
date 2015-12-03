type MapObjectId = number;
type MapObjectType = string;

/**
 * Objects that can be clicked and that are associated with 
 * server-side information that can be used in various machine
 * learning / data visualization procedures.
 *
 * The property `type` should correspond to the object type
 * descriptor that is used on the server. An example for such a type
 * could be 'cell' or 'nucleus' etc.
 *
 * The id attribute should identify a object uniquely within its type.
 */
class MapObject {

    constructor(public id: MapObjectId,
                public type: MapObjectType,
                public visualType: string,
                public extraData: any) {}

    getVisual() {
        switch (this.visualType) {
            case 'polygon':
                return new PolygonVisual(this.extraData.coordinates, {
                    fillColor: Color.WHITE.withAlpha(0.02),
                    strokeColor: Color.WHITE
                });
                break;
            default:
                throw new Error('Unknown visual type');
        }
    }
}
