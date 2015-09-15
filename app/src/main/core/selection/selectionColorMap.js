// angular.module('tmaps.core.selection')
// .factory('selectionColorMap', ['Color', function(Color) {
//     var colorsRGBString = ['rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)','rgb(255,127,0)','rgb(255,255,51)','rgb(166,86,40)','rgb(247,129,191)','rgb(153,153,153)'];

//     var colors = _(colorsRGBString).map(function(rgb) {
//         return Color.fromRGBString(rgb);
//     });

//     return {
//         getMappableIds: function() {
//             return _.range(colors.length);
//         },
//         getColorForId: function(id) {
//             if (id < colors.length) {
//                 return colors[id];
//             } else {
//                 throw new Error('No color specified for id: ' + id);
//             }
//         }
//     };
// }]);

