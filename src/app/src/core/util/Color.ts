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
interface SerializedColor extends Serialized<Color> {
    r: number;
    g: number;
    b: number;
    a: number;
}

class Color implements Serializable<Color> {

    private _rgbComponentToHex(c: number): string {
        var hex = c.toString(16);
        return hex.length == 1 ? "0" + hex : hex;
    }

    get r() {
        return this._r;
    }

    get g() {
        return this._g;
    }

    get b() {
        return this._b;
    }

    get a() {
        return this._a;
    }

    constructor(private _r: number,
                private _g: number,
                private _b: number,
                private _a: number = 1.0) {}

    toOlColor(): ol.Color {
        return [this._r, this._g, this._b, this._a];
    }

    toRGBAString(): string {
        return 'rgba(' + this._r + ', ' + this._g + ', ' + this._b + ', ' +  this._a + ')';
    }

    toRGBString(): string {
        return 'rgb(' + this._r + ', ' + this._g + ', ' + this._b + ')';
    }

    toHex(): string {
        return '#' + this._rgbComponentToHex(this._r) +
                     this._rgbComponentToHex(this._g) +
                     this._rgbComponentToHex(this._b);
    }

    toNormalizedRGBArray(): number[] {
        return [this._r / 255, this._g / 255, this._b / 255];
    }

    equals(other: Color) {
        return this._r == other.r && this._g == other.g && this._b == other.b && this._a == other.a;
    }

    withRed(r: number) {
        return new Color(r, this._g, this._b, this._a);
    }

    withGreen(g: number) {
        return new Color(this._r, g, this._b, this._a);
    }

    withBlue(b: number) {
        return new Color(this._r, this._g, b, this._a);
    }

    withAlpha(a: number) {
        return new Color(this._r, this._g, this._b, a);
    }

    serialize() {
        return $injector.get<ng.IQService>('$q').when({
            r: this._r, g: this._g, b: this._b, a: this._a
        });
    }

    /*
     * Convert a hex string like '#ffffff' to a RGB
     * color given as an array of numbers between 0 and 1.
     */
    static fromHex(hex: string, alpha: number = 1): Color {
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

    static fromNormalizedRGBArray(arr: number[]): Color {
        var denorm = _.map(arr, function(component) {
            return Math.floor(component * 255);
        });
        return new Color(denorm[0], denorm[1], denorm[2], 1.0);
    }

    static fromRGBString(rgb: string) {
        var res = /^\s*rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\)\s*$/.exec(rgb);
        if (res === null || res.length != 4) {
            return undefined;
        } else {
            return new Color(parseInt(res[1]), parseInt(res[2]), parseInt(res[3]));
        }
    }

    static fromObject(o: {r: number; g: number; b: number; a?: number;}): Color {
        var alpha = o.a === undefined ? 1 : o.a;
        return new Color(o.r, o.g, o.b, alpha);
    }

    static fromOlColor(c: ol.Color) {
        return new Color(c[0], c[1], c[2], c[3]);
    }

    static get RED() {
        return new Color(255, 0, 0);
    }

    static get GREEN() {
        return new Color(0, 255, 0);
    }

    static get BLUE() {
        return new Color(0, 0, 255);
    }

    static get WHITE() {
        return new Color(255, 255, 255);
    }

    static get BLACK() {
        return new Color(0, 0, 0);
    }
}

angular.module('tmaps.core')
.factory('Color', () => {
    return Color;
});

