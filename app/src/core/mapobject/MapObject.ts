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
interface MapObject extends Visualizable {
    id: MapObjectId;
    type: MapObjectType;
}
