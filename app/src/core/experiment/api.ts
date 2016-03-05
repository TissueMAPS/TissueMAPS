interface GetExperimentResponse {
    owned: ExperimentAPIObject[];
    shared: ExperimentAPIObject[];
}

interface LayerAPIObject {
    name: string;
    imageSize: ImageSize;
    pyramidPath: string;
}

interface MapObjectInfoAPIObject {
    map_object_name: string;
    features: {name: string; }[];
}

interface ExperimentAPIObject {
    id: string;
    name: string;
    description: string;
    owner: string;
    layers: LayerAPIObject[];
    map_object_info: MapObjectInfoAPIObject[];
}
