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
interface WorkflowStageDescription {
    name: string;
    active: boolean;
    mode: string;
    steps: WorkflowStepDescription[];
}


class WorkflowStage extends JobCollection {
    name: string;
    active: boolean;
    mode: string;
    steps: WorkflowStep[];

    constructor(description: WorkflowStageDescription,
                workflowStageStatus: any) {
        super(workflowStageStatus);
        this.name = description.name;
        this.mode = description.mode;
        if (description.steps != null) {
            // NOTE: due to hack for "upload" stage, which doens't have any steps
            this.steps = description.steps.map((step, index) => {
                var workflowStepStatus = null;
                if (workflowStageStatus != null) {
                    workflowStepStatus = workflowStageStatus.subtasks[index];
                }
                return new WorkflowStep(step, workflowStepStatus);
            });
        }
    }

    private _isUploadOk() {
        return this.status.done && !this.status.failed;
    }

    check(): boolean {
        if (this.name == 'upload') {
            return this._isUploadOk();
        }
        var areStepsOk: boolean[] = this.steps.map((step) => {
            return step.check();
        });
        return _.all(areStepsOk);
    }

    getDescription(): WorkflowStageDescription {
        return {
            name: this.name,
            mode: this.mode,
            active: this.active,
            steps: this.steps.map((step, idx) => {
                return step.getDescription();
            })
        }
    }
}

