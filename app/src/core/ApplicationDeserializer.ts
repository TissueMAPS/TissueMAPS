class ApplicationDeserializer implements Deserializer<Application> {

    static $inject = [
        'application', 'viewportDeserializer', '$q'
    ];

    constructor(private application: Application,
                private viewportDeser: ViewportDeserializer,
                private $q: ng.IQService) {}

    deserialize(ser: SerializedApplication) {

        var viewports = _(ser.viewports).map((vpSer) => {
            var vpPromise: ng.IPromise<Viewport> = this.viewportDeser.deserialize(vpSer);
            return vpPromise.then((vp) => {
                vp.element.then((elem) => {
                    elem.hide();
                });
                this.application.viewports.push(vp);
                return vp;
            });
        });
        return this.$q.all(viewports).then((vps) => {
            this.application.setActiveViewportByNumber(ser.activeViewportNumber);
            return this.application;
        });
    }
}

angular.module('tmaps.core').service('applicationDeserializer', ApplicationDeserializer);

