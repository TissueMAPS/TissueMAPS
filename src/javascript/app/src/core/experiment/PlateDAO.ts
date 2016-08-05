interface SerializedPlate {
    id: string;
    name: string;
    description: string;
    experiment_id: string;
    acquisitions: SerializedAcquisition[];
    status: string;
}

class PlateDAO extends HTTPDataAccessObject<Plate> {
    /**
     * @classdesc An DataAccessObject for querying and creating objects
     * of type Plate.
     */
    constructor(experimentId: string) {
        super('/api/experiments/' + experimentId + '/plates')
    }

    fromJSON(data: SerializedPlate) {
        return new Plate({
            id: data.id,
            name: data.name,
            description: data.description,
            experiment_id: data.experiment_id,
            acquisitions: data.acquisitions.map((acq) => {
                return (new AcquisitionDAO(data.experiment_id)).fromJSON(acq);
            }),
            status: data.status
        });
    }
}
