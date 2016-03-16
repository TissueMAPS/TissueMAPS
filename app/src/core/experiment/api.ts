interface GetExperimentResponse {
    owned: ExperimentAPIObject[];
    shared: ExperimentAPIObject[];
}

interface LayerAPIObject {
    id: string;
    name: string;
    image_size: {
        width: number;
        height: number;
    };
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
