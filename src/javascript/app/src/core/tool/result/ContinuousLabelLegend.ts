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

        for (var i = min; i <= max; i += step) {
            imageData.push([i]);
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
       for (i = min, j = 0; i <= max; i += step, j++) {
           if (j % 10 == 0) {
               annotations.push({
                   x: 0.51,
                   y: j,
                   text: Math.floor(i * 100) / 100,
                   xanchor: 'left',
                   yanchor: 'center',
                   showarrow: false,
                   font: {
                       color: 'white',
                       size: 14
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
