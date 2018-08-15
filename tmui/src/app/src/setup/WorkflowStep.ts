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
interface WorkflowStepDescription {
    name: string;
    active: boolean;
    batch_args: any;
    submission_args: any;
    extra_args: any;
    fullname: string;
    help: string;
}


class WorkflowStep extends JobCollection {
    name: string;
    active: boolean;
    batch_args: Argument[];
    submission_args: Argument[];
    extra_args: Argument[];
    fullname: string;
    help: string;

    constructor(description: WorkflowStepDescription,
                workflowStepStatus: any) {
        super(workflowStepStatus);
        this.name = description.name;
        this.active = description.active;
        this.fullname = description.fullname;
        this.help = description.help;
        this.batch_args = description.batch_args.map((arg) => {
            return new Argument(arg);
        });
        this.submission_args = description.submission_args.map((arg) => {
            return new Argument(arg);
        });
        if (description.extra_args != null) {
            this.extra_args = description.extra_args.map((arg) => {
                return new Argument(arg);
            });
        }
    }

    getDescription(): WorkflowStepDescription {
        return {
            name: this.name,
            batch_args: this.batch_args,
            submission_args: this.submission_args,
            extra_args: this.extra_args,
            active: this.active,
            help: this.help,
            fullname: this.fullname
        }
    }

    private _checkArgs(args: Argument[]) {
        return _.chain(args).map((arg) => {
            var isValid;
            if (arg.required) {
                isValid = arg.value !== undefined
                    && arg.value !== null
                    && arg.value !== '';
            } else {
                isValid = true;
            }
            return isValid;
        }).all().value();
    }

    check() {
        var workflowStatusArgsAreValid, batchArgsAreValid, extraArgsAreValid;
        var isValid: boolean;

        batchArgsAreValid = this._checkArgs(this.batch_args);
        workflowStatusArgsAreValid = this._checkArgs(this.submission_args);

        if (this.extra_args) {
            extraArgsAreValid = this._checkArgs(this.extra_args);
        } else {
            extraArgsAreValid = true;
        }

        return batchArgsAreValid && workflowStatusArgsAreValid && extraArgsAreValid;
    }
}
