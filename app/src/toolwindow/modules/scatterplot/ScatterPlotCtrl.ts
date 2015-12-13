class ScatterPlotCtrl {

    highchartConfig: any;
    private _tool: ScatterPlotTool;
    private _xData: any;
    private _yData: any;

    static $inject = ['$scope', 'tmapsProxy'];

    constructor($scope, tmapsProxy) {
        this._tool = tmapsProxy.tool;
        var mapObjectManager = tmapsProxy.appInstance.mapObjectManager;
        var viewport = tmapsProxy.appInstance.viewport;
        // CHART OPTIONS
        this.highchartConfig = {
            options: {
                chart: {
                    type: 'scatter',
                    zoomType: 'xy',
                    backgroundColor: 'rgba(255, 255, 255, 0)'
                },
                plotOptions: {
                    series:  {
                        cursor: 'pointer',
                        point: {
                            events: {
                                click: (e) => {
                                    console.log(e);
                                    var type = $scope.toolOptions.chosenMapObjectType;
                                    var id = e.point.index;
                                    mapObjectManager.getMapObjectsById(type, [id]).then((objs) => {
                                        viewport.goToMapObject(objs[0]);
                                    });
                                }
                            }
                        }
                    },
                    scatter: {
                        marker: {
                            states: {
                                hover: {
                                    enabled: true
                                }
                            }
                        }
                    }
                    // area: {
                    //     pointStart: 0,
                    //     pointInterval: 1
                    // },
                    // areaspline: {
                    //     fillOpacity: 0.5,
                    //     pointStart: 0,
                    //     pointInterval: 1
                    // }
                    // column: {
                    //     grouping: false,
                    //     shadow: false,
                    //     groupPadding: 0,
                    //     pointPadding: 0,
                    //     borderWidth: 0
                    // }
                }
            },
            xAxis: {
                title: {
                    text: ''
                }
            },
            yAxis: {
                title: {
                    text: ''
                }
            },
            series: [],
            title: {
                text: ''
            },
            loading: false
        };

        $scope.$on('featureSelected', (evt, feat, widget) => {
            this._tool.fetchFeatureData(feat.mapObjectType, feat.name)
            .then((data) => {
                var newData = {
                    name: feat.name,
                    data: data
                };

                if (widget.name === 'featureWidgetX') {
                    this._xData = newData;
                }
                if (widget.name === 'featureWidgetY') {
                    this._yData = newData;
                }
                if (this._xData !== undefined && this._yData !== undefined) {
                    var nDataPoints = data.length;
                    var i;
                    var seriesData = [];
                    for (i = 0; i < nDataPoints; i++) {
                        seriesData.push(
                            // {
                            // x: this._xData.data[i],
                            // y: this._yData.data[i],
                            // type: feat.mapObjectType,
                            // id: i
                        // }
                            [this._xData.data[i], this._yData.data[i]]
                        
                        );
                    }
                    this.highchartConfig.series = [
                        {
                            name: 'Data',
                            data: seriesData
                        }
                    ];
                    this.highchartConfig.xAxis.text = this._xData.name;
                    this.highchartConfig.yAxis.text = this._yData.name;
                    this.highchartConfig.title.text = this._xData.name + ' vs. ' + this._yData.name;
                    $scope.$apply();
                }
            });
        });

        $scope.$on('featureDeselected', (evt, feat, widget) => {
            if (widget.name === 'featureWidgetX') {
                this._xData = undefined;
            }
            if (widget.name === 'featureWidgetY') {
                this._yData = undefined;
            }
        });
    }
}

angular.module('tmaps.toolwindow')
.controller('ScatterPlotCtrl', ScatterPlotCtrl);

    // var lastSelection = {};

    // // CHART OPTIONS
    // $scope.highchartConfig = {
        // options: {
            // chart: {
            //     type: 'areaspline'
            //     // ,
            //     // backgroundColor: 'rgba(255, 255, 255, 0)',
            //     // animation: false
            // },
            // plotOptions: {
            //     // area: {
            //     //     pointStart: 0,
            //     //     pointInterval: 1
            //     // },
            //     areaspline: {
            //         fillOpacity: 0.5,
            //         pointStart: 0,
            //         pointInterval: 1
            //     }
            //     // column: {
            //     //     grouping: false,
            //     //     shadow: false,
            //     //     groupPadding: 0,
            //     //     pointPadding: 0,
            //     //     borderWidth: 0
            //     // }
            // }
        // },
        // yAxis: {
            // min: 0,
            // title: {
            //     text: 'density'
            // }
        // },
        // series: [],
        // title: {
            // text: ''
        // },
        // loading: false
    // };

    // $scope.featSelectionChanged = function(selectedFeatures) {

        // lastSelection = selectedFeatures;

        // // There is only one feature since we set 'single-selection = "true"'
        // // on the tmFeatureSelectionWidget.
        // var feature = selectedFeatures[0];

        // var selections = tmapsProxy.viewport.selectionHandler.selections;

        // // Create a mapping of the sort String => List[Int]
        // var selectedCells = {};
        // _.each(selections, function(sel) {
            // selectedCells[sel.name] = sel.getCells();
        // });

        // var payload = {
            // feature: feature,
            // selected_cells: selectedCells
        // };

        // toolInstance.sendRequest(payload).then(function(data) {

            // var newSeries = [];
            // var midpoints = data.histogram_midpoints;

            // _.each(data.histograms, function(hist) {

            //     var histogram = hist.histogram;
            //     var values = hist.values;

            //     var selectionName = hist.selection_name;
            //     console.log(data);

            //     var selectionObject = _(selections).find(function(sel) {
            //         return sel.name === selectionName;
            //     });

            //     var selectionColor = selectionObject.getColor().toRGBAString();

            //     newSeries.push({
            //         name: selectionName,
            //         data: histogram,
            //         color: selectionColor
            //     });
            // });


            // var intervalLength = (midpoints[0] + midpoints[1]) / 2;
            // var startingPoint = midpoints[0];

            // $scope.highchartConfig.options.plotOptions.areaspline.pointStart = startingPoint;
            // $scope.highchartConfig.options.plotOptions.areaspline.pointInterval = intervalLength;
            // $scope.highchartConfig.series = newSeries;
            // $scope.highchartConfig.title.text = feature.name;
        // });
    // };

    // tmapsProxy.$rootScope.$on('cellSelectionChanged', function(sel) {
        // $scope.featSelectionChanged(lastSelection);
    // });

// }]);

