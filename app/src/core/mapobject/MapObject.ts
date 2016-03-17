/**
 * Objects that can be clicked and that are associated with 
 * server-side information that can be used in various machine
 * learning / data visualization procedures.
 *
 * The property `type` should correspond to the object type
 * descriptor that is used on the server. An example for such a type
 * could be 'cell' or 'nucleus' etc.
 *
 * The id attribute should identify a object uniquely.
 */
type MapObjectType = string;

class MapObject {

    id: number;
    type: MapObjectType;
    outline: PolygonCoordinates;

    constructor(id: number, type: MapObjectType, outline) {
        this.id = id;
        this.type = type;
        this.outline = outline;
    }


    getVisual(): ColorizableVisual {
        var visual = new PolygonVisual(this.outline);
        // Set this mapobject as a property on the visual's underlying
        // openlayers feature, so this information can be restored when the user
        // clicks on the feature.
        var feat = <any> visual.olFeature;
        feat.set('mapObject', this);
        return visual;
    }
}
