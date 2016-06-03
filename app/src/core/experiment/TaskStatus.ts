interface TaskStatusArgs {
    cpu_time: string;
    exitcode: number;
    memory: number;
    name: string;
    state: string;
    time: string;
    failed: boolean;
    is_done: boolean;
    percent_done: number;
}

class TaskStatus {
    cpu_time: string;
    exitcode: number;
    memory: number;
    state: string;
    name: string;
    time: string;
    failed: boolean;
    is_done: boolean;
    percent_done: number;

    /**
     * Constructor a new Plate object.
     *
     * @class TaskStatus
     * @classdesc A plate is basically a container for multiple objects
     * of type Acquisition.
     * @param {TasksStatusArgs} args - Constructor arguments.
     */
    constructor(args: TaskStatusArgs) {
        this.cpu_time = args.cpu_time;
        this.exitcode = args.exitcode;
        this.is_done = args.is_done;
        this.failed = args.failed;
        this.name = args.name;
        this.state = args.state;
        this.percent_done = args.percent_done;
        this.memory = args.memory;
        this.time = args.time;
    }

}
