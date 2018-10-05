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
interface ArgumentDescription {
    name: string;
    value: any;
    default: any;
    choices: any[];
    help: string;
    required: boolean;
    disabled: boolean;
}


class Argument {
    name: string;
    value: any;
    default: any;
    choices: any[];
    help: string;
    required: boolean;
    disabled: boolean;

    constructor(args: ArgumentDescription) {
        this.name = args.name;
        this.value = args.value;
        this.default = args.default;
        this.choices = args.choices;
        this.help = args.help;
        this.required = args.required;
        this.disabled = args.disabled;
    }
}
