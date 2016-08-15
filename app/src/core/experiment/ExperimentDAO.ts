interface SerializedExperiment {
    id: string;
    name: string;
    description: string;
    user: string;
    plate_format: string;
    microscope_type: string;
    plate_acquisition_mode: string;
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
