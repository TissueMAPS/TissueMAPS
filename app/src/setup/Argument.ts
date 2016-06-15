interface ArgumentArgs {
    name: string;
    value: any;
    default: any;
    choices: any[];
    help: string;
    type: string;
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

    constructor(args: ArgumentArgs) {
        this.name = args.name;
        this.value = args.value;
        this.default = args.default;
        this.choices = args.choices;
        this.help = args.help;
        this.required = args.required;
        this.disabled = args.disabled;
    }
}
