class HeatmapLabelLayer extends LabelLayer {
    getLabelColorMapper() {
        return (label) => {
            var normLabel = (label - this.attributes.min) / (this.attributes.max - this.attributes.min);
            var rescaledLabel = 255 * normLabel;
            return new Color(255, 255 - rescaledLabel, 255 - rescaledLabel);
        };
    }
    
    getLegend() {
        return new ContinuousLabelLegend({
            min: this.attributes.min, 
            max: this.attributes.max
        });
    }
}
