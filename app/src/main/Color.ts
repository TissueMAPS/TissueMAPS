class Color implements Serializable<Color> {

    private rgbComponentToHex(c: number): string {
        var hex = c.toString(16);
        return hex.length == 1 ? "0" + hex : hex;
    }

    constructor(private $q: ng.IQService,
                public r: number,
                public g: number,
                public b: number,
                public a: number = 1.0) {}

    toRGBAString(): string {
        return 'rgba(' + this.r + ', ' + this.g + ', ' + this.b + ', ' +  this.a + ')';
    }

    toRGBString(): string {
        return 'rgb(' + this.r + ', ' + this.g + ', ' + this.b + ')';
    }

    toHex(): string {
        return '#' + this.rgbComponentToHex(this.r * 255) +
                     this.rgbComponentToHex(this.g * 255) +
                     this.rgbComponentToHex(this.b * 255);
    }

    toNormalizedRGBArray(): number[] {
        return [this.r / 255, this.g / 255, this.b / 255];
    }

    serialize() {
        return this.$q.when({
            r: this.r, g: this.g, b: this.b, a: this.a
        });
    }

}

class ColorFactory {

    static $inject = ['$q'];
    constructor(private $q: ng.IQService) {}

    /*
     * Convert a hex string like '#ffffff' to a RGB
     * color given as an array of numbers between 0 and 1.
     */
    createFromHex(hex: string, alpha: number): Color {
        // Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
        var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
        hex = hex.replace(shorthandRegex, function(m, r, g, b) {
            return r + r + g + g + b + b;
        });
        var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        if (result) {
            return this.create(
                parseInt(result[1], 16),
                parseInt(result[2], 16),
                parseInt(result[3], 16)
            );
        } else {
            return null;
        }
    }

    createFromNormalizedRGBArray(arr: number[]): Color {
        var denorm = _.map(arr, function(component) {
            return Math.floor(component * 255);
        });
        return this.create(denorm[0], denorm[1], denorm[2], 1.0);
    }

    create(r: number, g: number, b: number, a: number = 1.0): Color {
        return new Color(this.$q, r, g, b, a)
    }

    createFromRGBString(rgb: string) {
        var res = /^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/.exec(rgb);
        if (res === null) {
            return undefined;
        } else {
            return this.create(parseInt(res[0]),
                               parseInt(res[1]),
                               parseInt(res[2]));
        }
    }
}

angular.module('tmaps.core').service('ColorFactory', ColorFactory);

interface SerializedColor extends Serialized<Color> {
    r: number;
    g: number;
    b: number;
    a: number;
}

class ColorDeserializer implements Deserializer<Color> {
    static $inject = ['ColorFactory', '$q'];
    constructor(private colorFty: ColorFactory, private $q: ng.IQService) {}
    deserialize(col: SerializedColor) {
        var color = this.colorFty.create(col.r, col.g, col.b, col.a);
        return this.$q.when(color);
    }
}

angular.module('tmaps.core').service('ColorDeserializer', ColorDeserializer);
