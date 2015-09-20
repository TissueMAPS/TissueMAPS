interface GetAppstatesResponse {
    owned: AppstateAPIObject[];
    shared: AppstateAPIObject[];
}

interface AppstateAPIObject {
    id: string;
    name: string;
    owner: string;
    is_snapshot: boolean;
    blueprint: SerializedApplication;
}

