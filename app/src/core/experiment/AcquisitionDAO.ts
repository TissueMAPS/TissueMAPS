interface SerializedAcquisition {
    id: string;
    name: string;
    description: string;
    status: string;
}

class AcquisitionDAO extends HTTPDataAccessObject<Acquisition> {

    /**
     * @classdesc A DataAccessObject for the Acquisition class.
     */
    constructor(experimentId: string) {
        super('/api/experiments/' + experimentId + '/acquisitions')
    }

    fromJSON(aq: SerializedAcquisition) {
        return new Acquisition({
            id: aq.id,
            name: aq.name,
            status: aq.status,
            description: aq.description
        });
    }
}
