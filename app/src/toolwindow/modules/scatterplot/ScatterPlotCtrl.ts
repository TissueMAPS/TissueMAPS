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

angular.module('tmaps.toolwindow').controller('ScatterPlotCtrl', ScatterPlotCtrl);
