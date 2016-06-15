class Job {
    name: string;
    status: JobStatus;
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
