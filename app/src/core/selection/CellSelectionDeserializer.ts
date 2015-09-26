class CellSelectionDeserializer implements Deserializer<CellSelection> {
    static $inject = ['colorDeserializer', 'cellSelectionFactory', '$q'];
    constructor(private colorDeserializer: ColorDeserializer,
                private fty: CellSelectionFactory,
                private $q: ng.IQService) {}

    deserialize(ser: SerializedCellSelection) {
        var color = this.colorDeserializer.deserialize(ser.color);
        return color.then((col) => {
            var sel = this.fty.create(ser.id, col);
            for (var cellId in ser.cells) {
                var markerPos = ser.cells[cellId];
                sel.addCell(markerPos, cellId);
            }
            return this.$q.when(sel);
        });
    }
}

angular.module('tmaps.core.selection').service('cellSelectionDeserializer', CellSelectionDeserializer);
