class HeatmapResult extends LabelResult {
    getLabelColorMapper() {
        return (label) => {
            var normLabel = (label - this.attributes.min) / this.attributes.max;
            return new Color(0, 256 * normLabel, 0);
        };
    }
}
