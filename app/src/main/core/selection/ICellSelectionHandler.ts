interface SerializedSelectionHandler extends Serialized<CellSelectionHandler> {

}

class CellSelectionHandler implements Serializable<CellSelectionHandler> {

    constructor(private $q: ng.IQService) {}

    serialize() {
        var obj = <Serializable<CellSelectionHandler>> {};
        return this.$q.when(obj);
    }
}


