class SupervisedClassifierLabelLayer extends LabelLayer {
    getLabelColorMapper() {
        var colorMap = {};
        // Convert from hex strings to Color objects
        for (var label in this.attributes.color_map) {
            colorMap[label] = Color.fromHex(this.attributes.color_map[label]);
        }
        return (label) => {
            return colorMap[label];
        };
    }

    getLegend() {
        return new ScalarLabelLegend({
            colors: _.values(this.attributes.color_map).map((c) => {
                return Color.fromHex(c);
            }),
            labels: _.keys(this.attributes.color_map)
        });
    }
}
