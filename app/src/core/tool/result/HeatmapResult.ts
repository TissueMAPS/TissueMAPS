class HeatmapResult extends LabelResult {
    /**
     * Return a function that maps a label that was assigned to a map
     * object to a color which can be used to colorize the
     * object's polygon on the map.
     */
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
}
