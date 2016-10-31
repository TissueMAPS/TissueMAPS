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
// class ScatterPlotCtrl {

//     highchartConfig: any;
//     private _tool: ScatterPlotTool;
//     private _xData: any;
//     private _yData: any;

//     static $inject = ['$scope', 'tmapsProxy'];

//     constructor($scope, tmapsProxy) {
//         this._tool = tmapsProxy.tool;
//         var mapObjectRegistry = tmapsProxy.viewer.mapObjectRegistry;
//         var viewport = tmapsProxy.viewer.viewport;
//         // CHART OPTIONS
//         this.highchartConfig = {
//             options: {
//                 chart: {
//                     type: 'scatter',
//                     zoomType: 'xy',
//                     backgroundColor: 'rgba(255, 255, 255, 0)'
//                 },
//                 plotOptions: {
//                     series:  {
//                         turboThreshold: 10000,
//                         cursor: 'pointer',
//                         point: {
//                             events: {
//                                 click: (e) => {
//                                     var type = $scope.toolOptions.chosenMapObjectType;
//                                     var id = e.point.id;
//                                     mapObjectRegistry.getMapObjectsById(type, [id]).then((objs) => {
//                                         viewport.goToMapObject(objs[0]);
//                                     });
//                                 }
//                             }
//                         }
//                     },
//                     scatter: {
//                         marker: {
//                             states: {
//                                 hover: {
//                                     enabled: true
//                                 }
//                             }
//                         }
//                     }
//                 }
//             },
//             xAxis: {
//                 title: {
//                     text: ''
//                 }
//             },
//             yAxis: {
//                 title: {
//                     text: ''
//                 }
//             },
//             series: [],
//             title: {
//                 text: ''
//             },
//             loading: false
//         };

//         $scope.$on('featureSelected', (evt, feat, widget) => {
//             this._tool.fetchFeatureData(feat.mapObjectType, feat.name)
//             .then((newData: FeatureData) => {
//                 if (widget.name === 'featureWidgetX') {
//                     this._xData = newData;
//                 }
//                 if (widget.name === 'featureWidgetY') {
//                     this._yData = newData;
//                 }
//                 if (this._xData !== undefined && this._yData !== undefined) {
//                     var nDataPoints = newData.values.length;
//                     var i;
//                     var seriesData = [];
//                     for (i = 0; i < nDataPoints; i++) {
//                         seriesData.push({
//                             id: newData.ids[i],
//                             name: newData.ids[i],
//                             x: this._xData.values[i],
//                             y: this._yData.values[i]
//                         });
//                     }
//                     this.highchartConfig.series = [
//                         {
//                             name: 'Data',
//                             data: seriesData
//                         }
//                     ];
//                     this.highchartConfig.xAxis.text = this._xData.name;
//                     this.highchartConfig.yAxis.text = this._yData.name;
//                     this.highchartConfig.title.text = this._xData.name + ' vs. ' + this._yData.name;
//                     $scope.$apply();
//                 }
//             });
//         });

//         $scope.$on('featureDeselected', (evt, feat, widget) => {
//             if (widget.name === 'featureWidgetX') {
//                 this._xData = undefined;
//             }
//             if (widget.name === 'featureWidgetY') {
//                 this._yData = undefined;
//             }
//         });
//     }
// }

// angular.module('tmaps.ui').controller('ScatterPlotCtrl', ScatterPlotCtrl);
