class RestoreAppstateService {
    static $inject = [
        'application',
        'appInstanceFactory',
        'experimentFactory',
        'colorFactory',
        'cellSelectionHandlerFactory',
        'cellSelectionFactory',
        '$q'
    ];

    constructor(private app: Application,
                private appInstanceFty: AppInstanceFactory,
                private experimentFty: ExperimentFactory,
                private colorFty: ColorFactory,
                private cellSelectionHandlerFty: CellSelectionHandlerFactory,
                private cellSelectionFty: CellSelectionFactory,
                private $q: ng.IQService) {
    }

    restoreAppstate(appstate: Appstate) {
        var bp = appstate.blueprint;
        bp.appInstances.forEach((ai) => {
            var expArgs = <ExperimentArgs> ai.experiment;
            var exp = this.experimentFty.create(expArgs);
            var inst = this.appInstanceFty.create(exp);
            this.app.appInstances.push(inst);
            this.restoreAppInstance(inst, ai);
        });
        this.app.setActiveAppInstanceByNumber(bp.activeAppInstanceNumber);
    }

    private restoreAppInstance(inst: AppInstance, ai: SerializedAppInstance) {
        this.restoreViewport(inst.viewport, ai.viewport);
        // this.experiment.cells.then((cells) => {
        //     var cellLayer = this.objectLayerFactory.create('Cells', {
        //         objects: cells,
        //         fillColor: 'rgba(255, 0, 0, 0)',
        //         strokeColor: 'rgba(255, 0, 0, 1)'
        //     });
        //     this.viewport.addObjectLayer(cellLayer);
        // });
    }

    private restoreViewport(vp: Viewport, vpState: SerializedViewport) {
        // Create and initialize the selection handler
        var selHandler = this.cellSelectionHandlerFty.create(vp);
        this.restoreCellSelectionHandler(selHandler, vpState.selectionHandler);
        vp.setSelectionHandler(selHandler);

        // Add all layers
        vpState.channelLayerOptions.forEach((ch) => {
            // Colors were serialized as mere objects holding r, g, b.
            // We need to restore them to a full Color object.
            var color = this.colorFty.create(ch.color.r, ch.color.g, ch.color.b, ch.color.a);
            ch.color = color;
            vp.addChannelLayer(ch);
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

    private restoreCellSelectionHandler(csh: CellSelectionHandler,
                                        cshState: SerializedSelectionHandler) {
        var activeSelId = cshState.activeSelectionId;
        var selections = cshState.selections;
        selections.forEach((ser) => {
            var selColor = this.colorFty.createFromRGBAObject(ser.color);
            var sel = this.cellSelectionFty.create(ser.id, selColor);
            for (var cellId in ser.cells) {
                var markerPos = ser.cells[cellId];
                sel.addCell(markerPos, cellId);
            }
            csh.addSelection(sel);
        });
        if (activeSelId !== undefined) {
            csh.activeSelectionId = activeSelId;
        }
    }
}

angular.module('tmaps.core').service('restoreAppstateService', RestoreAppstateService);
