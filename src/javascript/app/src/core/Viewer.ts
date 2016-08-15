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

    private _$http: ng.IHttpService;
    private _$q: ng.IQService;

    mapObjectSelectionHandler: MapObjectSelectionHandler;
    tools: ng.IPromise<Tool[]>;
    channels: Channel[] = [];
    mapobjectTypes: MapobjectType[] = [];

    // TODO: A viewer should mayble be creatable without an experiment.
    // The initialization process of loading an experiment would be done by a
    // separate function.
    constructor(experiment: Experiment) {

        this._$http = $injector.get<ng.IHttpService>('$http');
        this._$q = $injector.get<ng.IQService>('$q');

        this.id = makeUUID();
        this.experiment = experiment;
        this.viewport = new Viewport();

        this.tools = this.getTools();

        console.log('instatiate viewer')
        this.experiment.getChannels()
        .then((channels) => {
            if (channels) {
                this.viewport.initMap(channels[0].layers[0].imageSize)
                channels.forEach((ch) => {
                    this.channels.push(ch);
                    this.viewport.addLayer(ch);
                });
            }
        })

        this.mapObjectSelectionHandler = new MapObjectSelectionHandler(this);
        this.experiment.getMapobjectTypes()
        .then((mapobjectTypes) => {
            // Subsequently add the selection handler and initialize the layers.
            // TODO: The process of adding the layers could be made nicer.
            // The view should be set independent of 'ChannelLayers' etc.
            if (mapobjectTypes) {
                mapobjectTypes.forEach((t) => {
                    this.mapobjectTypes.push(t);
                    this.mapObjectSelectionHandler.addMapObjectType(t.name);
                    this.mapObjectSelectionHandler.addNewSelection(t.name);
                });
            }
        })

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

    getTools(): ng.IPromise<any> {
        return this._$http.get('/api/tools')
        .then((resp: any) => {
            // console.log(resp)
            return resp.data.data.map((t) => {
                return new Tool(t);
            });
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
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
        this.channels.forEach((ch) => {
            ch.setPlane(this._currentZplane, t);
        });
        this._currentTpoint = t;
    }

    get currentZplane() {
        return this._currentZplane;
    }

    set currentZplane(z: number) {
        this.channels.forEach((ch) => {
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
        var url = '/api/experiments/' + this.experiment.id + '/tools/request';
        // TODO: Send event to Viewer messagebox
        var $http = $injector.get<ng.IHttpService>('$http');
        var request: ServerToolRequest = {
            session_uuid: session.uuid,
            payload: payload,
            tool_name: session.tool.name
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
            console.log('ToolService: HANDLE REQUEST.');
            var result = (new ToolResultDAO(this.experiment.id)).fromJSON(data.result);
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

    /**
     * The highest zoom level for any layer of this experiment.
     * It is assumed that all layers of an experiment have the same max
     * zoom level.
     * @type number
     */
    get maxZoom(): number {
        return this.channels[0].layers[0].maxZoom;
    }

    /**
     * The highest time point supported by this experiment.
     * @type number
     */
    get maxT(): number {
        if (this.channels) {
            var ts = this.channels.map((ch) => {
                return ch.maxT;
            });
            return Math.max.apply(this, ts);
        } else {
            return 0;
        }
    }

    /**
     * The lowest time point supported by this experiment.
     * @type number
     */
    get minT(): number {
        if (this.channels) {
            var ts = this.channels.map((ch) => {
                return ch.minT;
            });
            return Math.min.apply(this, ts);
        } else {
            return 0;
        }
    }

    /**
     * The highest zplane supported by this experiment.
     * @type number
     */
    get maxZ(): number {
        if (this.channels) {
            var zs = this.channels.map((ch) => {
                return ch.maxZ;
            });
            return Math.max.apply(this, zs);
        } else {
            return 0;
        }
    }

    /**
     * The lowest zplane supported by this experiment.
     * @type number
     */
    get minZ(): number {
        if (this.channels) {
            var zs = this.channels.map((ch) => {
                return ch.minZ;
            });
            return Math.min.apply(this, zs);
        } else {
            return 0;
        }
    }
}
