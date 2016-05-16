interface SerializedFeature {
    id: string;
    name: string;
}

interface SerializedMapobjectType {
    id: string;
    name: string;
    features: SerializedFeature[];
}

interface SerializedExperiment {
    id: string;
    name: string;
    description: string;
    user: string;
    plate_format: string;
    microscope_type: string;
    plate_acquisition_mode: string;
    status: string;
    channels: SerializedChannel[];
    mapobject_types: SerializedMapobjectType[];
    plates: SerializedPlate[];
    workflow_description: any;
}

class ExperimentDAO extends HTTPDataAccessObject<Experiment> {
    /**
     * @classdesc An DataAccessObject for querying and creating objects
     * of type Experiment.
     */
    constructor() {
        super('/api/experiments')
    }

    fromJSON(data: SerializedExperiment) {
        return new Experiment(data);
    }
}
