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
class ScalarLabelLayer extends LabelLayer {
    colors: Color[] = [
        '#a6cee3',
        '#1f78b4',
        '#b2df8a',
        '#33a02c',
        '#fb9a99',
        '#e31a1c',
        '#fdbf6f',
        '#ff7f00',
        '#cab2d6',
        '#6a3d9a',
        '#ffff99',
        '#b15928'
    ].map((c) => {
        return Color.fromHex(c);
    });

    getLabelColorMapper() {
        return (label) => {
            var idx = this.attributes.unique_labels.find((v, index) => {
                var precision = label.length - 2;
                if (precision < 0) {
                    precision = 0;
                }
                var vStr = v.toFixed(precision);
                return vStr == label;
            });
            if (idx % 2 == 0) {
                return this.colors[idx];
            } else {
                return this.colors[this.colors.length - idx];
            }
        };
    }
    
    getLegend() {
        var colors = [];
        var uniqueLabels = this.attributes.unique_labels;
        uniqueLabels.forEach((l) => {
            var idx = uniqueLabels.indexOf(l);
            if (idx % 2 == 0) {
                colors.push(this.colors[idx]);
            } else {
                colors.push(this.colors[this.colors.length - idx]);
            }
        })

        return new ScalarLabelLegend({
            colors: colors,
            labels: <string[]> this.attributes.unique_labels
        });
    }
}
