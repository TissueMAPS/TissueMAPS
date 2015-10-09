class Color implements Serializable<Color> {

    private rgbComponentToHex(c: number): string {
        var hex = c.toString(16);
        return hex.length == 1 ? "0" + hex : hex;
    }

    constructor(public r: number,
                public g: number,
                public b: number,
                public a: number = 1.0) {}

    toOlColor(): ol.Color {
        return [this.r, this.g, this.b, this.a];
    }

    toRGBAString(): string {
        return 'rgba(' + this.r + ', ' + this.g + ', ' + this.b + ', ' +  this.a + ')';
    }

    toRGBString(): string {
        return 'rgb(' + this.r + ', ' + this.g + ', ' + this.b + ')';
    }

    toHex(): string {
        return '#' + this.rgbComponentToHex(this.r) +
                     this.rgbComponentToHex(this.g) +
                     this.rgbComponentToHex(this.b);
    }

    toNormalizedRGBArray(): number[] {
        return [this.r / 255, this.g / 255, this.b / 255];
    }

    equals(other: Color) {
        return this.r == other.r && this.g == other.g && this.b == other.b && this.a == other.a;
    }

    serialize() {
        return $injector.get<ng.IQService>('$q').when({
            r: this.r, g: this.g, b: this.b, a: this.a
        });
    }

    /*
     * Convert a hex string like '#ffffff' to a RGB
     * color given as an array of numbers between 0 and 1.
     */
    static createFromHex(hex: string, alpha: number): Color {
        hex = hex.toLowerCase();
        // Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
        var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
        hex = hex.replace(shorthandRegex, function(m, r, g, b) {
            return r + r + g + g + b + b;
        });
        var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        if (result) {
            return new Color(
                parseInt(result[1], 16),
                parseInt(result[2], 16),
                parseInt(result[3], 16)
            );
        } else {
            return null;
        }
    }

    static createFromNormalizedRGBArray(arr: number[]): Color {
        var denorm = _.map(arr, function(component) {
            return Math.floor(component * 255);
        });
        return new Color(denorm[0], denorm[1], denorm[2], 1.0);
    }

    static createFromRGBString(rgb: string) {
        var res = /^\s*rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\)\s*$/.exec(rgb);
        if (res === null || res.length != 4) {
            return undefined;
        } else {
            return new Color(parseInt(res[1]), parseInt(res[2]), parseInt(res[3]));
        }
    }

    static createFromObject(o: {r: number; g: number; b: number; a?: number;}): Color {
        var alpha = o.a === undefined ? 1 : o.a;
        return new Color(o.r, o.g, o.b, alpha);
    }

}

// TODO: Remove this class
class ColorFactory {
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
        return new Color(r, g, b, a)
    }

    createFromRGBString(rgb: string) {
        var res = /^\s*rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\)\s*$/.exec(rgb);
        if (res === null || res.length != 4) {
            return undefined;
        } else {
            return this.create(parseInt(res[1]),
                               parseInt(res[2]),
                               parseInt(res[3]));
        }
    }

    createFromRGBAObject(o: {r: number; g: number; b: number; a: number;}): Color {
        return this.create(o.r, o.g, o.b, o.a);
    }
}

angular.module('tmaps.core').service('colorFactory', ColorFactory);

interface SerializedColor extends Serialized<Color> {
    r: number;
    g: number;
    b: number;
    a: number;
}
