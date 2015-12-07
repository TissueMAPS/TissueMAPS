class ResultLayer extends VisualLayer {
    constructor(name: string, opt: VisualLayerOpts = {}) {
        opt.contentType = ContentType.result;
        super(name, opt);
    }
}
