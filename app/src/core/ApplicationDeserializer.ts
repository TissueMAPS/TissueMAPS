class ApplicationDeserializer implements Deserializer<Application> {

    static $inject = [
        'application', 'appInstanceDeserializer', '$q'
    ];

    constructor(private application: Application,
                private appInstanceDeser: AppInstanceDeserializer,
                private $q: ng.IQService) {}

    deserialize(ser: SerializedApplication) {

        var appInstances = _(ser.appInstances).map((instSer) => {
            var instPromise: ng.IPromise<AppInstance> = this.appInstanceDeser.deserialize(instSer);
            return instPromise.then((inst) => {
                inst.setInactive();
                this.application.appInstances.push(inst);
                return inst;
            });
        });
        return this.$q.all(appInstances).then((insts) => {
            this.application.setActiveAppInstanceByNumber(ser.activeAppInstanceNumber);
            return this.application;
        });
    }
}

angular.module('tmaps.core').service('applicationDeserializer', ApplicationDeserializer);

