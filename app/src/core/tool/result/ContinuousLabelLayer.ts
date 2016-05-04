class ContinuousLabelLayer extends LabelLayer {
    getLabelColorMapper() {
        return (label) => {
            var normLabel = (label - this.attributes.min) / this.attributes.max;
            if (normLabel <= 0.5) {
                normLabel *= 2;
                var rescaledLabel = 255 * normLabel;
                return new Color(255, rescaledLabel, rescaledLabel);
            } else {
                var rescaledLabel = 255 * normLabel;
                return new Color(255 - rescaledLabel, 255 - rescaledLabel, 255);
            }
        };
    }

    getLegend() {
        return new SampleLegend();
    }
}
