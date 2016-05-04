abstract class Legend {
    abstract getElement(): Element;
}

class SampleLegend {

    constructor() {
    }

    getElement() {
       var img = document.createElement('img');
       img.width = 30;
       img.height = 100;
       img.src = 'http://i2.wp.com/www.r-bloggers.com/wp-content/uploads/2011/03/improved-legend.png';
       return img;

       var colors = ['red', 'blue', 'green'];
       var labels = [1, 2, 3];

       // var annotations = [];
       // var data = [];

       // for (var i = 0; i < labels.length; i++) {
       //     annotations.push({
       //         x: 0.5,
       //         y: (i + 1) * 10 - 5,
       //         text: labels[i],
       //         xanchor: 'center',
       //         yanchor: 'center',
       //         showarrow: false,
       //         font: {
       //             size: 38,
       //             style: 'bold'
       //         }
       //     });

       //     data.push({
       //         x: [0],
       //         y: [10],
       //         type: 'bar',
       //         color: colors[i]
       //     })
       // }

       // var layout = {
       // barmode: 'stack',
       // annotations: annotations,
       // xaxis: {
       //     ticks: false,
       //     zeroline: false,
       //     showgrid: false,
       //     showline: false,
       //     showticklabels: false,
       // },
       // yaxis: {
       //     showaxis: false,
       //     zeroline: false,
       //     ticks: false,
       //     showgrid: false,
       //     showline: false,
       //     showticklabels: false,
       // },
       // showlegend: false
       // };

       // var div = document.createElement('div');
       // Plotly.newPlot(div, data, layout);
    }
}
