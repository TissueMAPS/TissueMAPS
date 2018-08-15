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
interface ScalarLabelLegendArgs {
    labels: string[];
    colors: Color[];
}

class ScalarLabelLegend extends Legend {

    constructor(args: ScalarLabelLegendArgs) {
        var labels = args.labels;
        var colors = args.colors;
        var annotations = [];
        var data = [];

        var color;
        for (var i = 0; i < labels.length; i++) {
            var str = ('     ' + labels[i]).slice(-15);
            annotations.push({
                x: 6,
                y: (i + 1) * 10 - 5,
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

            data.push({
                x: [0],
                y: [10],
                type: 'bar',
                marker: {
                    color: colors[i].toHex()
                }
            })
        }

        var layout = {
            barmode: 'stack',
            annotations: annotations,
            xaxis: {
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
            showlegend: false,
            width: 220,
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

        var div = document.createElement('div');
        Plotly.newPlot(div, data, layout, {
            staticPlot: true
        });

        super($(div));
    }
}
