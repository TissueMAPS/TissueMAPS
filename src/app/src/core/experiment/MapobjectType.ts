/**
 * MapobjectType constructor arguments.
 */
interface MapobjectTypeArgs {
    id: string;
    name: string;
    features: SerializedFeature[];
    // experiment_id: string;
}


class MapobjectType {
    id: string;
    name: string;
    features: Feature[];
    // experimentId: string;

    constructor(args: MapobjectTypeArgs) {
        this.id = args.id;
        this.name = args.name;
        this.features = args.features;
        // this.experimentId = args.experiment_id;
    }
}
