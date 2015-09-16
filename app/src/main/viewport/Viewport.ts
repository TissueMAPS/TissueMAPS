interface Viewport {
    element: JQuery;
    scope: ng.IScope;
    controller: any;
    map: ol.Map;
}

interface ViewportScope extends ng.IScope {
    appInstance: AppInstance;
    // TODO: Set type to that of ViewportCtrl
    viewport: any;
}
