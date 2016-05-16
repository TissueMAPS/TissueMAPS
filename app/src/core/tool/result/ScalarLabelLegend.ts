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
            annotations.push({
                x: 0.60,
                y: (i + 1) * 10 - 5,
                text: labels[i],
                xanchor: 'center',
                yanchor: 'center',
                showarrow: false,
                font: {
                    size: 22,
                    color: 'white',
                    style: 'bold'
                }
            });

            data.push({
                x: [0],
                y: [10],
                type: 'bar',
                marker: {color: color}
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
