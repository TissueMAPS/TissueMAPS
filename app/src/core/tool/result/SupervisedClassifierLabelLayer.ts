class SupervisedClassifierLabelLayer extends LabelLayer {
    getLabelColorMapper() {
        var colorMap = this.attributes.color_map;
        // Convert from hex strings to Color objects
        for (var label in colorMap) {
            colorMap[label] = Color.fromHex(colorMap[label]);
        }
        return (label) => {
            return colorMap[label];
        };
    }

    getLegend() {
        return new ScalarLabelLegend({
            colors: _.values(this.attributes.color_map),
            labels: _.keys(this.attributes.color_map)
        });
    }
}
