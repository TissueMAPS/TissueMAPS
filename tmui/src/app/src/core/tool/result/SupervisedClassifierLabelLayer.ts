// Copyright (C) 2016-2018 University of Zurich.
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
class SupervisedClassifierLabelLayer extends LabelLayer {
    getLabelColorMapper() {
        var colorMap = {};
        // Convert from hex strings to Color objects
        for (var label in this.attributes.label_map) {
            colorMap[label] = Color.fromHex(this.attributes.label_map[label]['color']);
        }
        return (label) => {
            return colorMap[label];
        };
    }

    getLegend() {
        return new ScalarLabelLegend({
            colors: _.values(this.attributes.label_map).map((c) => {
                return Color.fromHex(c.color);
            }),
            labels: _.values(this.attributes.label_map).map((c) => {
                return c.name;
            })
        });
    }
}
