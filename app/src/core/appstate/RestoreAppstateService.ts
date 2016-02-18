class RestoreAppstateService {
    static $inject = [
        'application',
        '$q'
    ];

    constructor(private app: Application,
                private $q: ng.IQService) {
    }

    restoreAppstate(appstate: Appstate) {
        var bp = appstate.blueprint;
        bp.appInstances.forEach((ai) => {
            var expArgs = <ExperimentArgs> ai.experiment;
            var exp = new Experiment(expArgs);
            var inst = new AppInstance(exp);
            this.app.appInstances.push(inst);
            this.restoreAppInstance(inst, ai);
        });
        this.app.setActiveAppInstanceByNumber(bp.activeAppInstanceNumber);
    }

    private restoreAppInstance(inst: AppInstance, ai: SerializedAppInstance) {
        this.restoreViewport(inst.viewport, ai.viewport);
    }

    private restoreViewport(vp: Viewport, vpState: SerializedViewport) {
        // Create and initialize the selection handler
        // TODO
        // Add all layers
        vpState.channelLayerOptions.forEach((ch) => {
            // Colors were serialized as mere objects holding r, g, b.
            // We need to restore them to a full Color object.
            var color = new Color(ch.color.r, ch.color.g, ch.color.b, ch.color.a);
            ch.color = color;
            var layer = new ChannelLayer(ch);
            vp.addChannelLayer(layer);
        });

        // Restore the camera position
        vp.map.then(function(map) {
            var v = map.getView();
            v.setZoom(vpState.mapState.zoom);
            v.setCenter(vpState.mapState.center);
            v.setResolution(vpState.mapState.resolution);
            v.setRotation(vpState.mapState.rotation);
        });
    }

    private restoreSelectionHandler(csh: MapObjectSelectionHandler,
                                        cshState: SerializedSelectionHandler) {
        // var activeSelId = cshState.activeSelectionId;
        var selections = cshState.selections;
        selections.forEach((ser) => {
            var selColor = Color.fromObject(ser.color);
            // var sel = new MapObjectSelection(ser.id, selColor);
            // for (var cellId in ser.cells) {
            //     var markerPos = ser.cells[cellId];
            //     sel.addCell(markerPos, cellId);
            // }
            // csh.addSelection(sel);
        });
        // if (activeSelId !== undefined) {
        //     csh.activeSelectionId = activeSelId;
        // }
    }
}

angular.module('tmaps.core').service('restoreAppstateService', RestoreAppstateService);
