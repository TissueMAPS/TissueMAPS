interface SerializedPlate {
    id: string;
    name: string;
    description: string;
    experiment_id: string;
    acquisitions: SerializedAcquisition[];
}

class PlateDAO extends HTTPDataAccessObject<Plate> {
    constructor() {
        super('/api/plates')
    }

    fromJSON(data: SerializedPlate) {
        return new Plate({
            id: data.id,
            name: data.name,
            description: data.description,
            acquisitions: data.acquisitions.map((acq) => {
                return (new AcquisitionDAO()).fromJSON(acq);
            })
        });
    }
}
