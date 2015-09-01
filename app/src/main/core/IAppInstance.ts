interface IAppInstance {
    experiment: IExperiment;
    viewport: IViewport;
    map: ng.IPromise<ol.Map>;

    cycleLayers: any[];
    outlineLayers: any[];
    clickListeners: any;

    // selectionHandler: ICellSelectionHandler;

}
