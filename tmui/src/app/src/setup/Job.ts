// Copyright (C) 2016-2018 University of Zurich.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
class Job {
    id: string;
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
