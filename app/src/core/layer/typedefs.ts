type ImageSize = [number, number];

interface ModifiedOlTileLayer extends ol.layer.Tile {
    getMin(): number;
    setMin(val: number);
    getMax(): number;
    setMax(val: number);
    setColor(c: number[]);
    getColor(): number[];
    setAdditiveBlend(b: boolean);
    getAdditiveBlend(): boolean;
}

interface ModifiedOlTileLayerArgs extends olx.layer.LayerOptions {
    color: number[];  // for example: [1, 0, 0] == red
    additiveBlend: string;
    min?: number;
    max?: number;
}
