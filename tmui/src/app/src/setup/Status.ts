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
interface JobStatusArgs {
    name: string;
    done: boolean;
    failed: boolean;
    state: string;
    created_at: string;
    updated_at: string;
    percent_done: number;
    subtasks: any[];
    live: boolean;
    memory: number;
    type: string;
    exitcode: number;
    id: string;
    submission_id: number;
    time: string;
    cpu_time: string;
}


class JobCollectionStatus {
    done: boolean;
    failed: boolean;
    state: string;
    percentDone: number;

    constructor(args: JobStatusArgs) {
        if (args == null) {
            this.done = false;
            this.failed = false;
            this.percentDone = 0;
            this.state = '';
        } else {
            this.done = args.done;
            this.failed = args.failed;
            this.state = args.state;
            this.percentDone = args.percent_done;
        }
    }
}


class JobStatus {
    done: boolean;
    failed: boolean;
    state: string;
    memory: number;
    time: string;
    cpu_time: string;
    exitcode: number;

    constructor(args: JobStatusArgs) {
        this.done = args.done;
        this.failed = args.failed;
        this.state = args.state;
        this.memory = args.memory;
        this.time = args.time;
        this.cpu_time = args.cpu_time;
        this.exitcode = args.exitcode;
    }


    getLogOuput() {

    }

}
