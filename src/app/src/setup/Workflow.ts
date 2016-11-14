// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
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
interface WorkflowDescription {
    type: string;
    stages: WorkflowStageDescription[];
}


class Workflow extends JobCollection {
    type: string;
    stages: WorkflowStage[];

    constructor(description: WorkflowDescription,
                workflowStatus: any) {

        super(workflowStatus);
        this.type = description.type;
        var uploadStage = new WorkflowStage({
                name: 'upload',
                steps: [],
                active: true,
                mode: 'sequential'
            }, {
                done: false,
                failed: false,
                percent_done: 0,
                state: '',
                subtasks: []
        });
        var processingStages = description.stages.map((stage, index) => {
            var workflowStageStatus = null;
            if (workflowStatus != null) {
                if (index < workflowStatus.subtasks.length) {
                   workflowStageStatus = workflowStatus.subtasks[index];
                }
            }
            return new WorkflowStage(stage, workflowStageStatus);
        });
        this.stages = [uploadStage].concat(processingStages);
    }

    check(index: number): boolean {
        if (index == null || index == undefined) {
            index = this.stages.length - 1;
        }
        return this.stages.every((stage, idx) => {
            if (idx <= index) {
                return stage.check();
            } else {
                // subsequent step which don't get submitted
                // are not checked here
                return true;
            }
        });
    }

    getDescription(index: number): WorkflowDescription {
        return {
            type: this.type,
            stages: this.stages.map((stage, idx) => {
                if (idx > 0 && stage.name != 'upload') {
                    // skip "upload" stage
                    var stageDescription = stage.getDescription();
                    if (idx <= index) {
                        stageDescription.active = true;
                    } else {
                        stageDescription.active = false;
                    }
                    return stageDescription;
                }
            })
            .filter((stage) => {
                return stage != undefined;
            })
        }
    }

}
