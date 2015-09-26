interface Appstate {
    id: string;
    name: string;
    isSnapshot: boolean;
    owner: string;
    blueprint: SerializedApplication;
}
