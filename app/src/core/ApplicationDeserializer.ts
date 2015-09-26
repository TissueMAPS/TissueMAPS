class ApplicationDeserializer implements Deserializer<Application> {

    static $inject = [
        'application', 'viewportDeserializer', '$q'
    ];

    constructor(private application: Application,
                private viewportDeser: ViewportDeserializer,
                private $q: ng.IQService) {}

    deserialize(ser: SerializedApplication) {

        var viewports = _(ser.viewports).map((instSer) => {
            var instPromise: ng.IPromise<Viewport> = this.viewportDeser.deserialize(instSer);
            return instPromise.then((inst) => {
                inst.setInactive();
                this.application.viewports.push(inst);
                return inst;
            });
        });
        return this.$q.all(viewports).then((vps) => {
            this.application.setActiveViewportByNumber(ser.activeViewportNumber);
            return this.application;
        });
    }
}

angular.module('tmaps.core').service('applicationDeserializer', ApplicationDeserializer);

