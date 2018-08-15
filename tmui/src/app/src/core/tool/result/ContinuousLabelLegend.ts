// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
// Copyright 2018 University of Zurich
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
interface ContinuousLabelLegendArgs {
    min: number;
    max: number;
}

class ContinuousLabelLegend extends Legend {

    constructor(args: ContinuousLabelLegendArgs) {
        var min = args.min;
        var max = args.max;
        var imageData = [];
        var step = (max - min) / 100;

        for (var i = 0; i < 100; i++) {
            imageData.push([min + i*step]);
        }

        var colorscale = [
            ['0', 'rgb(255, 255, 255)'],
            ['1', 'rgb(255, 0, 0)']
        ];

        var data = [{
            z: imageData,
            colorscale: colorscale,
            type: 'heatmap',
            showscale: false
        }];

       var annotations = [];

       var i: number;
       var j: number;
       for (j = 0; j < 100; j++) {
           i = min + j*step;
           if (j % 10 == 0) {
               var val = Math.floor(i * 100) / 100;
               var str = ('     ' + val).slice(-15);
               annotations.push({
                   x: 12,
                   y: j,
                   text: str,
                   xanchor: 'right',
                   yanchor: 'center',
                   showarrow: false,
                   font: {
                       size: 10,
                       color: 'white',
                       style: 'bold'
                   }
               });
           }
       }

       var layout = {
           annotations: annotations,
           xaxis: {
               showaxis: false,
               ticks: '',
               zeroline: false,
               showgrid: false,
               showline: false,
               showticklabels: false,
           },
           yaxis: {
               showaxis: false,
               zeroline: false,
               ticks: '',
               showgrid: false,
               showline: false,
               showticklabels: false,
           },
           width: 250,
           paper_bgcolor: 'rgba(0,0,0,0)',
           plot_bgcolor: 'rgba(0,0,0,0)',
           margins: {
               l: 0,
               r: 0,
               b: 0,
               t: 0,
               pad: 0
           }
       };

        var elem = document.createElement('div');

        Plotly.newPlot(elem, data, layout, {
            staticPlot: true
        });

        super($(elem));
     }
}
