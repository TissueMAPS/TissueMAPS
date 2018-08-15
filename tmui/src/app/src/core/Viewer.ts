// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

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
    private _$interval: ng.IIntervalService;

    mapObjectSelectionHandler: MapObjectSelectionHandler;
    tools: ng.IPromise<Tool[]>;
    channels: Channel[] = [];
    mapobjectTypes: MapobjectType[] = [];
    isSubmissionHandled: any = {};


    // TODO: A viewer should mayble be creatable without an experiment.
    // The initialization process of loading an experiment would be done by a
    // separate function.
    constructor(experiment: Experiment) {

        this._$http = $injector.get<ng.IHttpService>('$http');
        this._$q = $injector.get<ng.IQService>('$q');
        this._$interval = $injector.get<ng.IIntervalService>('$interval');

        this.id = makeUUID();
        this.experiment = experiment;
        this.viewport = new Viewport();

        this.tools = this.getTools();

        console.log('instatiate viewer')
        this.mapObjectSelectionHandler = new MapObjectSelectionHandler(this);
        this.experiment.getChannels()
        .then((channels) => {
            if (channels) {
                this.viewport.initMap(channels[0].layers[0].imageSize)
                channels.forEach((ch) => {
                    // The mapSize attribute is important for SegmentationLayers
                    this.viewport.mapSize = {
                        height: ch.height, width: ch.width
                    };
                    this.channels.push(ch);
                    this.viewport.addLayer(ch);
                });
            }
        })

        // We need to ensure that segmentation layers are created after
        // the channels, because otherwise the mapSize might be
        // incorrect.
        this.experiment.getMapobjectTypes()
        .then((mapobjectTypes) => {
            // Subsequently add the selection handler and initialize the layers.
            // TODO: The process of adding the layers could be made nicer.
            // The view should be set independent of 'ChannelLayers' etc.
            if (mapobjectTypes) {
                mapobjectTypes.forEach((t) => {
                    this.mapobjectTypes.push(t);
                    this.mapObjectSelectionHandler.addMapobjectType(t);
                    this.mapObjectSelectionHandler.addNewSelection(t.name);
                });
            }
        })
        // // DEBUG
        // var segmLayer = new SegmentationLayer('DEBUG_TILE', {
        //     tpoint: 0,
        //     experimentId: this.experiment.id,
        //     zplane: 0,
        //     size: this.viewport.mapSize,
        //     visible: false
        // });
        // segmLayer.strokeColor = Color.RED;
        // segmLayer.fillColor = Color.WHITE.withAlpha(0);
        // this.viewport.addLayer(segmLayer);

        this._getExistingToolResults();

    }

    getTools(): ng.IPromise<any> {
        return this._$http.get('/api/tools')
        .then((resp: any) => {
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

    hasCurrentResult() {
        return this._currentResult !== null;
    }

    get currentTpoint() {
        return this._currentTpoint;
    }

    set currentTpoint(t: number) {
        this.channels.forEach((ch) => {
            ch.setPlane(this._currentZplane, t);
        });
        this.mapobjectTypes.forEach((mt) => {
            mt.setPlane(this._currentZplane, t);
        })
        this._currentTpoint = t;
    }

    get currentZplane() {
        return this._currentZplane;
    }

    set currentZplane(z: number) {
        this.channels.forEach((ch) => {
            ch.setPlane(z, this._currentTpoint);
        });
        this.mapobjectTypes.forEach((mt) => {
            mt.setPlane(z, this._currentTpoint);
        })
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

    /**
     * Handle the result of a successful tool response.
     * @param data The response that was received by the server.
     * This object also contains the tool-specific result object.
     */
    private _handleSuccessfulToolResult(res: SerializedToolResult) {
        // TODO: Send event to Viewer messagebox
        // var sessionUUID = data.session_uuid;
        var result = (new ToolResultDAO(this.experiment.id)).fromJSON(res);
        result.attachToViewer(this);
        result.visible = false;
        // session.isRunning = false;
        // session.results.push(result);
        if (this.currentResult !== null) {
            if (result.submissionId > this.currentResult.submissionId) {
                this.saveCurrentResult();
                this.currentResult = result;
            } else {
                if (result.submissionId != this.currentResult.submissionId) {
                    var submissionIds = this.savedResults.map((res) => {
                        return res.submissionId;
                    })
                    if (submissionIds.indexOf(result.submissionId) == -1) {
                        this.savedResults.push(result);
                    }
                }
            }
        } else {
            this.currentResult = result;
        }
        // TODO: Send event to Viewer messagebox
    }


    /**
     * Given a submissionId of a job, query the server for this job's result and, if
     * there is such a result, add it to the viewer.
     */
    private _getAndHandleToolResult(submissionId: number) {
        return this._$http.get('/api/experiments/' + this.experiment.id + '/tools/results?submission_id=' + submissionId)
        .then((resp: any) => {
            var results = resp.data.data;
            if (results.length === 0) {
                console.log('ERROR: No result found with submission_id ' + submissionId);
            } else if (results.length > 1) {
                console.log('ERROR: Multiple results founds for submission_id ' + submissionId);
            } else {
                var result = results[0];
                this._handleSuccessfulToolResult(result);
                return result;
            }
        }, (resp) => {
            console.log(resp.data);
        });
    }

    private _getExistingToolResults() {
        // Get existing results
        this._$http.get('/api/experiments/' + this.experiment.id + '/tools/results')
        .then((resp: any) => {
            var results = resp.data.data;
            _(results).each((result) => {
                this._handleSuccessfulToolResult(result);
            });
        });

        // Query the server for running jobs and start monitoring their status
        this._$http.get('/api/experiments/' + this.experiment.id + '/tools/jobs?state=RUNNING')
        .then((resp: any) => {
            var jobStati = resp.data.data;
            _(jobStati).each((st) => {
                this._startMonitoringForToolResult(st.submission_id);
            });
        });
    }

    /**
     * Start polling the server for the status of the job with id `submissionId`.
     * If the job terminated successfully, the result it produced should be
     * added to the viewer.
     */
    private _startMonitoringForToolResult(submissionId: number) {
        var subscription;
        var monitor = () => {
            this._$http.get('/api/experiments/' + this.experiment.id + '/tools/jobs?submission_id=' + submissionId)
            .then((resp: any) => {
                var results = resp.data.data;
                if (results.length === 0) {
                    console.log('ERROR: No result found with submission_id ' + submissionId);
                } else if (results.length > 1) {
                    console.log('ERROR: Multiple results founds for submission_id ' + submissionId);
                } else {
                    var st = results[0];
                    var didJobEnd = st.state === 'TERMINATING' || st.state === 'TERMINATED';
                    var jobSuccessful = didJobEnd && st.exitcode === 0;
                    var jobFailed = st.state === didJobEnd && st.exitcode == 1;
                    if (didJobEnd) {
                        this._$interval.cancel(subscription);
                    }
                    if (jobSuccessful) {
                        this._getAndHandleToolResult(st.submission_id);
                    }
                    if (jobFailed) {
                        // TODO: Handle error
                    }
                }
            });
        };
        subscription = this._$interval(monitor, 5000);
    }


    /**
     * Send a request to the server-side tool to start a processing job.
     * The server will respond with a JSON object that containts a 'status'
     * property. If this property evaluates to 'ok' then the processing
     * was started successfully and the server should be queried for a tool
     * result by long-polling.
     * @param session The tool session
     * @param payload An object containing information that is understood by
     * the a particular server-side tool.
     * @type ng.IPromise<boolean>
     */
    sendToolRequest(session: ToolSession, payload: any) {
        var url = '/api/experiments/' + this.experiment.id + '/tools/request';
        var $http = $injector.get<ng.IHttpService>('$http');
        var request: ServerToolRequest = {
            session_uuid: session.uuid,
            payload: payload,
            tool_name: session.tool.name
        };
        console.log('ToolService: START REQUEST.');
        return $http.post(url, request).then(
        (resp: any) => {
            if (resp.data.data) {
                var submissionId = resp.data.data.submission_id;
                this._startMonitoringForToolResult(submissionId);
                var dialogService = $injector.get<DialogService>('dialogService');
                dialogService.info('Job submission successful!');
                return true;
            } else {
                return false;
            }
        },
        (err) => {
            // TODO: Dialog to show that submission was successful
            return false;
        });
    }

    // /**
    //  * The highest zoom level for any layer of this experiment.
    //  * It is assumed that all layers of an experiment have the same max
    //  * zoom level.
    //  * @type number
    //  */
    // get maxZoom(): number {
    //     return this.channels[0].layers[0].maxZoom;
    // }

    /**
     * The highest time point supported by this experiment.
     * @type number
     */
    get maxT(): number {
        if (this.channels.length > 0) {
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
        if (this.channels.length > 0) {
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
        if (this.channels.length > 0) {
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
        if (this.channels.length > 0) {
            var zs = this.channels.map((ch) => {
                return ch.minZ;
            });
            return Math.min.apply(this, zs);
        } else {
            return 0;
        }
    }
}
