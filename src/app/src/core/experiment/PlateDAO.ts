interface SerializedPlate {
    id: string;
    name: string;
    description: string;
    acquisitions: SerializedAcquisition[];
    status: string;
}

class PlateDAO extends HTTPDataAccessObject<Plate> {

    experimentId: string;
    /**
     * @classdesc An DataAccessObject for querying and creating objects
     * of type Plate.
     */
    constructor(experimentId: string) {
        super('/api/experiments/' + experimentId + '/plates')
        this.experimentId = experimentId;
    }

    fromJSON(data: SerializedPlate) {
        return new Plate({
            id: data.id,
            name: data.name,
            description: data.description,
            acquisitions: data.acquisitions.map((acq) => {
                return (new AcquisitionDAO(this.experimentId)).fromJSON(acq);
            }),
            status: data.status
        });
    }
}
