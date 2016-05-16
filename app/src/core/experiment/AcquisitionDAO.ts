interface SerializedAcquisition {
    id: string;
    name: string;
    description: string;
    plate_id: string;
    status: string;
    microscope_image_files: MicroscopeFile[];
    microscope_metadata_files: MicroscopeFile[];
}

class AcquisitionDAO extends HTTPDataAccessObject<Acquisition> {
    /**
     * @classdesc A DataAccessObject for the Acquisition class.
     */
    constructor() {
        super('/api/acquisitions')
    }

    fromJSON(aq: SerializedAcquisition) {
        return new Acquisition({
            id: aq.id,
            name: aq.name,
            status: aq.status,
            description: aq.description,
            files: aq.microscope_image_files.concat(aq.microscope_metadata_files)
        });
    }
}
