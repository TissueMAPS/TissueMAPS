class Job {
    id: number;
    dbId: number;
    phase: string;
    status: JobStatus;

    constructor(args: StatusArgs) {
        var startIdx = args.name.lastIndexOf('_') + 1;
        this.id = Number(args.name.substring(startIdx));
        this.dbId = args.id;
        if (args.type == 'RunJob') {
            this.phase = 'run';
        } else {
            this.phase = 'collect';
        }
        this.status = new JobStatus(args);
    }
}


class JobCollection {
    name: string;
    status: JobCollectionStatus;

    constructor(args: any) {
        if (args != null) {
            this.status = new JobCollectionStatus(args);
        } else {
            this.status = null;
        }
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
