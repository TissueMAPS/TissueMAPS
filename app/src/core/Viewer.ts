// interface SerializedAppInstance extends Serialized<AppInstance> {
//     experiment: SerializedExperiment;
//     viewport: SerializedViewport;
// }

// TODO: Rename to Viewer
class AppInstance {
    id: string;

    experiment: Experiment;
    viewport: Viewport;
    currentResult: ToolResult;
    savedResults: ToolResult[] = [];
    private _currentZplane = 0;

    private _element: JQuery = null;

    mapObjectSelectionHandler: MapObjectSelectionHandler;
    tools: ng.IPromise<Tool[]>;

    constructor(experiment: Experiment) {
        this.id = makeUUID();
        this.experiment = experiment;
        this.viewport = new Viewport();
        this.tools = Tool.getAll();

        this.viewport.initMap(this.experiment.channels[0].layers[0].imageSize)

        this.experiment.channels.forEach((ch) => {
            this.viewport.addLayer(ch);
        });

        // Subsequently add the selection handler and initialize the selection layers.
        // TODO: The process of adding the layers could be made nicer.
        // The view should be set independent of 'ChannelLayers' etc.
        this.mapObjectSelectionHandler = new MapObjectSelectionHandler(this);
        this.experiment.mapObjectNames.forEach((name) => {
            this.mapObjectSelectionHandler.addMapObjectType(name);
            this.mapObjectSelectionHandler.addNewSelection(name);
        });

        // DEBUG
        var segmLayer = new SegmentationLayer('DEBUG_TILE', {
            t: 0,
            experimentId: this.experiment.id,
            zlevel: 0,
            size: this.viewport.mapSize,
            visible: true
        });
        segmLayer.strokeColor = Color.RED;
        segmLayer.fillColor = Color.WHITE.withAlpha(0);
        this.viewport.addLayer(segmLayer);
    }

    saveCurrentResult() {
        this.savedResults.push(this.currentResult);
        this.currentResult = undefined;
    }

    get currentZplane() {
        return this._currentZplane;
    }

    set currentZplane(z: number) {
        this.experiment.channels.forEach((ch) => {
            ch.setZplane(z);
        });
        this._currentZplane = z;
    }

    destroy() {
        var elem = this._getDOMElement();
        elem.remove();
    }

    private _getDOMElement(): JQuery {
        if (this._element === null || this._element.length == 0) {
            var $document = $injector.get<ng.IDocumentService>('$document');
            this._element = $document.find('#viewer-'+ this.id);
        }
        return this._element;
    }

    hide() {
        this._getDOMElement().hide();
    }

    show() {
        this._getDOMElement().show();
        this.viewport.update();
    }

    // serialize(): ng.IPromise<SerializedAppInstance> {
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
        return $http.post(url, request).then(
        (resp) => {
            // TODO: Send event to Viewer messagebox
            // vpScope.$broadcast('toolRequestDone');
            // vpScope.$broadcast('toolRequestSuccess');
            var data = <ServerToolResponse> resp.data;
            var sessionUUID = data.session_uuid;
            var toolId = data.tool_id;
            console.log('ToolService: HANDLE REQUEST.');
            var result = ToolResult.createToolResult(session, data);
            session.isRunning = false;
            session.results.push(data.payload);
            this.currentResult = result;
            result.show(this);

            console.log('ToolService: DONE.');
            return data.payload;
        },
        (err) => {
            // this.appInstance.viewport.elementScope.then((vpScope) => {
                // TODO: Send event to Viewer messagebox
                // vpScope.$broadcast('toolRequestDone');
                // vpScope.$broadcast('toolRequestFailed', err.data);
            // });
            return err.data;
        });

    }
}
