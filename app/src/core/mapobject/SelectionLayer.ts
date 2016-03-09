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

interface SelectionLayerOpts {
    color: Color;
    visible?: boolean;
}

class SelectionLayer extends VisualLayer {
    color: Color;

    constructor(name: string, opt: SelectionLayerOpts) {
        super(name, { visible: opt.visible });
        this.color = opt.color;
        var size = 42; // Compute via resolution
        // Avoid whitespaces in image name
        var colorRgbString = this.color.toRGBString().replace(/\s/g, '');
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
