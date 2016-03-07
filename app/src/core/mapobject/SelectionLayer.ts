declare type SelectionId = number;

class MarkerImageVisual extends Visual {
    // mapObjectMarkers: {};
    color: Color;

    constructor(position: MapPosition, color: Color) {
        // TODO: Maybe the size of the marker icon should be
        // changed according to the current resolution
        // var styleFunc = (feature: ol.Feature, resolution: number) => {
        //     var size = 42; // Compute via resolution
        //     // Avoid whitespaces in image name
        //     var colorRgbString = color.toRGBString().replace(/\s/g, '');
        //     var imageSrc =
        //         'resources/img/marker/marker-' + colorRgbString + '-' + size +'.png';
        //     var style = new ol.style.Style({
        //         image: new ol.style.Icon({
        //             // the bottom of the marker should point to the mapObject's
        //             // center
        //             anchor: [0.5, 0.9],
        //             src: imageSrc
        //         })
        //     });
        //     return [style];
        // };
        // var size = 42; // Compute via resolution
        // // Avoid whitespaces in image name
        // var colorRgbString = color.toRGBString().replace(/\s/g, '');
        // var imageSrc =
        //     'resources/img/marker/marker-' + colorRgbString + '-' + size +'.png';
        // var style = new ol.style.Style({
        //     image: new ol.style.Icon({
        //         // the bottom of the marker should point to the mapObject's
        //         // center
        //         anchor: [0.5, 0.9],
        //         src: imageSrc
        //     })
        // });
        var olFeature = new ol.Feature({
            // style: styleFunc,
            geometry: new ol.geom.Point([position.x, position.y])
        });

        super(olFeature);

        this.color = color;
    }
}

class SelectionLayer extends VisualLayer {
    color: Color;

    constructor(name: string, color: Color) {
        super(name, {
            contentType: ContentType.marker
        })
        this.color = color;
        var size = 42; // Compute via resolution
        // Avoid whitespaces in image name
        var colorRgbString = color.toRGBString().replace(/\s/g, '');
        var imageSrc =
            'resources/img/marker/marker-' + colorRgbString + '-' + size +'.png';
        var style = new ol.style.Style({
            image: new ol.style.Icon({
                // the bottom of the marker should point to the mapObject's
                // center
                anchor: [0.5, 0.9],
                src: imageSrc
            })
        });

        console.log(style);
        this._olLayer.setStyle(style);
    }
}
// class SelectionLayer extends BaseLayer<ol.layer.Vector> {

//     color: Color;
//     mapObjectMarkers = {};

//     constructor(name: string,
//                 color: Color) {
//         super(name);

//         this.color = color;

//         // TODO: Maybe the size of the marker icon should be
//         // changed according to the current resolution
//         var styleFunc = (feature: ol.Feature, resolution: number) => {
//             var size = 42; // Compute via resolution
//             // Avoid whitespaces in image name
//             var colorRgbString = color.toRGBString().replace(/\s/g, '');
//             console.log('asdf');
//             var imageSrc =
//                 'resources/img/marker/marker-' + colorRgbString + '-' + size +'.png';
//             var style = new ol.style.Style({
//                 image: new ol.style.Icon({
//                     // the bottom of the marker should point to the mapObject's
//                     // center
//                     anchor: [0.5, 0.9],
//                     src: imageSrc
//                 })
//             });
//             return [style];
//         };

//         this._olLayer = new ol.layer.Vector({
//             source: new ol.source.Vector(),
//             style: styleFunc
//         });
//     }

//     addMapObjectMarker(mapObjectId: MapObjectId, position: MapPosition) {
//         if (!this.mapObjectMarkers.hasOwnProperty(mapObjectId.toString())) {
//             var feat = new ol.Feature({
//                 geometry: new ol.geom.Point([position.x, position.y])
//             });
//             var src = <ol.source.Vector> this._olLayer.getSource();
//             src.addFeature(feat);
//             this.mapObjectMarkers[mapObjectId] = feat;
//         }
//     }

//     removeMapObjectMarker(mapObjectId: MapObjectId) {
//         var feat = this.mapObjectMarkers[mapObjectId];
//         if (feat) {
//             var src = <ol.source.Vector> this._olLayer.getSource();
//             src.removeFeature(feat);
//             delete this.mapObjectMarkers[mapObjectId];
//         }
//     }

// }
