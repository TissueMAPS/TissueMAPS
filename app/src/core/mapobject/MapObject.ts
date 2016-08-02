/**
 * Objects that can be clicked and that are associated with 
 * server-side information that can be used in various machine
 * learning / data visualization procedures.
 *
 * The id attribute should identify a object uniquely.
 */

class MapObject {

    id: number;
    type: string;

    constructor(id: number, type: string) {
        this.id = id;
        this.type = type;
    }
}
