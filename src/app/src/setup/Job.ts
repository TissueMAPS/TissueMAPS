class Job {
    id: number;
    phase: string;
    status: JobStatus;

    constructor(args: JobStatusArgs) {
        var startIdx = args.name.lastIndexOf('_') + 1;
        this.id = args.id;
        if (args.type == 'RunJob') {
            this.phase = 'run';
        } else if (args.type == 'CollectJob') {
            this.phase = 'collect';
        } else if (args.type == 'InitJob') {
            this.phase = 'init';
        }
        this.status = new JobStatus(args);
    }
}


class JobCollection {
    name: string;
    status: JobCollectionStatus;

    constructor(args: any) {
        this.status = new JobCollectionStatus(args);
    }

    isWaiting(): boolean {
        if (this.status == undefined) {
            return true;
        } else {
            return this.status.state == '';
        }
    }

    isSubmitted(): boolean {
        if (this.status == undefined) {
            return false;
        } else {
            return this.status.state == 'SUBMITTED' || this.status.state == 'NEW';
        }
    }

    isRunning(): boolean {
        if (this.status == undefined) {
            return false;
        } else {
            return this.status.state == 'RUNNING';
        }
    }

}
