// interface SerializedViewer extends Serialized<Viewer> {
//     experiment: SerializedExperiment;
//     viewport: SerializedViewport;
// }
class Viewer {
    id: string;

    experiment: Experiment;
    viewport: Viewport;
    _currentResult: ToolResult = null;
    savedResults: ToolResult[] = [];

    // TODO: don't use zero as default but middle of z-stack
    private _currentTpoint = 0;
    private _currentZplane = 0;

    private _element: JQuery = null;

    mapObjectSelectionHandler: MapObjectSelectionHandler;
    tools: ng.IPromise<Tool[]>;

    // TODO: A viewer should mayble be creatable without an experiment.
    // The initialization process of loading an experiment would be done by a
    // separate function.
    constructor(experiment: Experiment) {
        this.id = makeUUID();
        this.experiment = experiment;
        this.viewport = new Viewport();
        this.tools = (new ToolDAO()).getAll();

        this.viewport.initMap(this.experiment.channels[0].layers[0].imageSize)

        this.experiment.channels.forEach((ch) => {
            this.viewport.addLayer(ch);
        });

        // Subsequently add the selection handler and initialize the selection layers.
        // TODO: The process of adding the layers could be made nicer.
        // The view should be set independent of 'ChannelLayers' etc.
        this.mapObjectSelectionHandler = new MapObjectSelectionHandler(this);
        this.experiment.mapobjectTypes.forEach((t) => {
            this.mapObjectSelectionHandler.addMapObjectType(t.name);
            this.mapObjectSelectionHandler.addNewSelection(t.name);
        });

        //// DEBUG
        // var segmLayer = new SegmentationLayer('DEBUG_TILE', {
        //     tpoint: 0,
        //     experimentId: this.experiment.id,
        //     zplane: 0,
        //     size: this.viewport.mapSize,
        //     visible: true
        // });
        // segmLayer.strokeColor = Color.RED;
        // segmLayer.fillColor = Color.WHITE.withAlpha(0);
        // this.viewport.addLayer(segmLayer);
    }

    get currentResult() {
        return this._currentResult;
    }

    set currentResult(r: ToolResult) {
        this.deleteCurrentResult();
        this._currentResult = r;
        this._hideAllSavedResults();
    }

    private _hideAllSavedResults() {
        this.savedResults.forEach((r) => {
            r.visible = false;
        });
    }

    private _deleteResult(res: ToolResult) {
        // TODO: Also completely remove the result
        res.visible = false;
    }

    deleteSavedResult(res: ToolResult) {
        var idx = this.savedResults.indexOf(res);
        if (idx > -1) {
            this._deleteResult(res);
            this.savedResults.splice(idx, 1);
        }
    }

    deleteCurrentResult() {
        if (this.currentResult !== null) {
            this._deleteResult(this.currentResult);
            this._currentResult = null;
        }
    }

    saveCurrentResult() {
        this.savedResults.push(this.currentResult);
        this._currentResult = null;
    }

    get currentTpoint() {
        return this._currentTpoint;
    }

    set currentTpoint(t: number) {
        this.experiment.channels.forEach((ch) => {
            ch.setPlane(this._currentZplane, t);
        });
        this._currentTpoint = t;
    }

    get currentZplane() {
        return this._currentZplane;
    }

    set currentZplane(z: number) {
        this.experiment.channels.forEach((ch) => {
            ch.setPlane(z, this._currentTpoint);
        });
        this._currentZplane = z;
    }

    destroy() {
        this.element.remove();
    }

    get element(): JQuery {
        if (this._element === null || this._element.length == 0) {
            var $document = $injector.get<ng.IDocumentService>('$document');
            this._element = $document.find('#viewer-'+ this.id);
        }
        return this._element;
    }

    hide() {
        this.element.hide();
    }

    show() {
        this.element.show();
        this.viewport.update();
    }

    // serialize(): ng.IPromise<SerializedViewer> {
    //     return $injector.get<ng.IQService>('$q').all({
    //         experiment: this.experiment.serialize(),
    //         viewport: this.viewport.serialize()
    //     }).then((res: any) => {
    //         return res;
    //     });
    // }

    sendToolRequest(session: ToolSession, payload: any) {
        var url = '/api/tools/' + session.tool.id + '/request';
        // TODO: Send event to Viewer messagebox
        var $http = $injector.get<ng.IHttpService>('$http');
        var request: ServerToolRequest = {
            experiment_id: this.experiment.id,
            session_uuid: session.uuid,
            payload: payload
        };
        console.log('ToolService: START REQUEST.');
        session.isRunning = true;
        var timeoutInMinutes = 120;
        return $http.post(url, request, {
            timeout: timeoutInMinutes * 1000 * 60
        }).then(
        (resp) => {
            // TODO: Send event to Viewer messagebox
            // vpScope.$broadcast('toolRequestDone');
            // vpScope.$broadcast('toolRequestSuccess');
            var data = <ServerToolResponse> resp.data;
            var sessionUUID = data.session_uuid;
            var toolId = data.tool_id;
            console.log('ToolService: HANDLE REQUEST.');
            var result = (new ToolResultDAO()).fromJSON(data.result);
            result.attachToViewer(this);
            session.isRunning = false;
            session.results.push(result);
            this.currentResult = result;
            result.visible = true;

            console.log('ToolService: DONE.');
            return data.result;
        },
        (err) => {
            // this.viewer.viewport.elementScope.then((vpScope) => {
                // TODO: Send event to Viewer messagebox
                // vpScope.$broadcast('toolRequestDone');
                // vpScope.$broadcast('toolRequestFailed', err.data);
            // });
            return err.data;
        });

    }
}
