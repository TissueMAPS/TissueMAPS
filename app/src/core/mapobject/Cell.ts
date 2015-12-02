// class Cell implements MapObject {

//     type = 'cell';
//     visualType = ''
//     position: MapPosition;

//     constructor(public id: number,
//                 public outline: PolygonCoordinates) {
//         var i;
//         var nCoords = outline.length;
//         var sumX = 0;
//         var sumY = 0;
//         for (i = 0; i < nCoords; i++) {
//             sumX += outline[i][0];
//             sumY += outline[i][1];
//         }
//         this.position = {
//             x: sumX / nCoords, y: sumY / nCoords
//         };
//     }

//     getVisual(): Visual {
//         return new PolygonVisual(this.outline);
//     }
// }

// angular.module('tmaps.core')
// .factory('Cell', () => {
//     return Cell;
// });
