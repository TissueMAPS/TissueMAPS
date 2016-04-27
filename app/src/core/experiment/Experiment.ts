interface CreateExperimentArgs {
    name: string;
    description: string;
    plateFormat: number;
    microscopeType: string;
    plateAcquisitionMode: string;
}

type ExperimentArgs = SerializedExperiment;

interface MapobjectType {
    id: string;
    name: string;
    features: Feature[];
}

class Experiment implements Model {
    id: string;
    name: string;
    description: string;
    plateFormat: string;
    microscopeType: string;
    mapobjectTypes: MapobjectType[];
    plateAcquisitionMode: string;
    channels: Channel[] = [];
    status: string;

    constructor(args: ExperimentArgs) {

        var $q = $injector.get<ng.IQService>('$q');

        this.id = args.id;
        this.name = args.name;
        this.description = args.description;
        this.status = args.status;
        this.plateFormat = args.plate_format;
        this.microscopeType = args.microscope_type;
        this.plateAcquisitionMode = args.plate_acquisition_mode;
        this.mapobjectTypes = args.mapobject_types;

        args.channels.forEach((ch) => {
            var isFirstChannel = this.channels.length == 0;
            var channel = new Channel(_.extend(ch, {
                visible: isFirstChannel
            }));
            this.channels.push(channel);
        });
    }

    get maxZ(): number {
        var zs = this.channels.map((ch) => {
            return ch.maxZ;
        });
        return Math.max.apply(this, zs);
    }

    get minZ(): number {
        var zs = this.channels.map((ch) => {
            return ch.minZ;
        });
        return Math.min.apply(this, zs);
    }
}
