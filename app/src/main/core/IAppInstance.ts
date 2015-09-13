interface AppInstance {
    experiment: Experiment;
    viewport: Viewport;
    map: ng.IPromise<ol.Map>;

    cycleLayers: any[];
    outlineLayers: any[];
    clickListeners: any;

    // selectionHandler: ICellSelectionHandler;

}
