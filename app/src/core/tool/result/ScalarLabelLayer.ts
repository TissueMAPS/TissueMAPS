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
            var idx = this.attributes.unique_labels.indexOf(label);
            if (idx % 2 == 0) {
                return this.colors[idx];
            } else {
                return this.colors[this.colors.length - idx];
            }
        };
    }
    
    getLegend() {
        return new SampleLegend();
    }
}
