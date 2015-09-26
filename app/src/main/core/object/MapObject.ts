interface MapObject {
    id: string;
    position: MapPosition;
    getOLFeature(): ol.Feature;
}
