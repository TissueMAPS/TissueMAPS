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
// angular.module('tmaps.ui')
// .controller('FeatureStatsCtrl',
//             ['$scope', '$rootScope', 'toolInstance', 'tmapsProxy',
//             function($scope, $rootScope, toolInstance, tmapsProxy) {

//     var lastSelection = {};

//     // CHART OPTIONS
//     $scope.highchartConfig = {
//         options: {
//             chart: {
//                 type: 'areaspline'
//                 // ,
//                 // backgroundColor: 'rgba(255, 255, 255, 0)',
//                 // animation: false
//             },
//             plotOptions: {
//                 // area: {
//                 //     pointStart: 0,
//                 //     pointInterval: 1
//                 // },
//                 areaspline: {
//                     fillOpacity: 0.5,
//                     pointStart: 0,
//                     pointInterval: 1
//                 }
//                 // column: {
//                 //     grouping: false,
//                 //     shadow: false,
//                 //     groupPadding: 0,
//                 //     pointPadding: 0,
//                 //     borderWidth: 0
//                 // }
//             }
//         },
//         yAxis: {
//             min: 0,
//             title: {
//                 text: 'density'
//             }
//         },
//         series: [],
//         title: {
//             text: ''
//         },
//         loading: false
//     };

//     $scope.featSelectionChanged = function(selectedFeatures) {

//         lastSelection = selectedFeatures;

//         // There is only one feature since we set 'single-selection = "true"'
//         // on the tmFeatureSelectionWidget.
//         var feature = selectedFeatures[0];

//         var selections = tmapsProxy.viewport.selectionHandler.selections;

//         // Create a mapping of the sort String => List[Int]
//         var selectedCells = {};
//         _.each(selections, function(sel) {
//             selectedCells[sel.name] = sel.getCells();
//         });

//         var payload = {
//             feature: feature,
//             selected_cells: selectedCells
//         };

//         toolInstance.sendRequest(payload).then(function(data) {

//             var newSeries = [];
//             var midpoints = data.histogram_midpoints;

//             _.each(data.histograms, function(hist) {

//                 var histogram = hist.histogram;
//                 var values = hist.values;

//                 var selectionName = hist.selection_name;
//                 console.log(data);

//                 var selectionObject = _(selections).find(function(sel) {
//                     return sel.name === selectionName;
//                 });

//                 var selectionColor = selectionObject.getColor().toRGBAString();

//                 newSeries.push({
//                     name: selectionName,
//                     data: histogram,
//                     color: selectionColor
//                 });
//             });


//             var intervalLength = (midpoints[0] + midpoints[1]) / 2;
//             var startingPoint = midpoints[0];

//             $scope.highchartConfig.options.plotOptions.areaspline.pointStart = startingPoint;
//             $scope.highchartConfig.options.plotOptions.areaspline.pointInterval = intervalLength;
//             $scope.highchartConfig.series = newSeries;
//             $scope.highchartConfig.title.text = feature.name;
//         });
//     };

//     tmapsProxy.$rootScope.$on('cellSelectionChanged', function(sel) {
//         $scope.featSelectionChanged(lastSelection);
//     });

// }]);

