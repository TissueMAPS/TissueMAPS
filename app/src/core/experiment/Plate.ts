interface PlateArgs {
    id: string;
    name: string;
    description: string;
    acquisitions: Acquisition[];
}

interface CreatePlateArgs {
    name: string;
    description: string;
}

class Plate {

    id: string;
    name: string;
    description: string;
    acquisitions: Acquisition[];

    constructor(args: PlateArgs) {
        this.id = args.id;
        this.name = args.name;
        this.description = args.description;
        this.acquisitions = args.acquisitions;
    }
}
