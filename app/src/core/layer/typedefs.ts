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
    getDrawWhitePixels(): boolean;
    setDrawWhitePixels(b: boolean);
    getDrawBlackPixels(): boolean;
    setDrawBlackPixels(b: boolean);
}

interface ModifiedOlTileLayerArgs extends olx.layer.LayerOptions {
    color: Color;
    additiveBlend: string;
    drawBlackPixels: boolean;
    drawWhitePixels: boolean;
    min?: number;
    max?: number;
}
