interface SerializedTaskStatus {
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

class TaskStatusDAO extends HTTPDataAccessObject<TaskStatus> {
    /**
     * @classdesc An DataAccessObject for querying and creating objects
     * of type Plate.
     */
    constructor() {
        super('/api/status')
    }

    fromJSON(data: SerializedTaskStatus) {
        return new TaskStatus({
            cpu_time: data.cpu_time,
            exitcode: data.exitcode,
            memory: data.memory,
            name: data.name,
            time: data.time,
            state: data.state,
            failed: data.failed,
            is_done: data.is_done,
            percent_done: data.percent_done
        });
    }
}
